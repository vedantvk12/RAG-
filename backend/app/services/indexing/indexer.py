import asyncio
from uuid import UUID
from typing import List

from qdrant_client.models import PointStruct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models import Document, DocumentChunk
from app.db.qdrant import get_qdrant_client
from app.schemas.qdrant import QdrantPayload
from app.llm.fastembed_provider import FastEmbedProvider

# Dependency injection / initialization for provider
provider = FastEmbedProvider()

async def index_document_background(doc_id: UUID):
    """
    Background task to index a document's chunks into Qdrant.
    Handles failures safely and leaves document in a recoverable state.
    """
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if not doc or doc.status != "ready":
            return
            
        doc.status = "indexing"
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        try:
            # 1. Fetch chunks
            result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.doc_id == doc.id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunks = result.scalars().all()
            
            if not chunks:
                doc.status = "indexed"
                db.add(doc)
                await db.commit()
                return

            # 2. Prepare batches
            batch_size = 100
            qdrant = get_qdrant_client()
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i+batch_size]
                texts = [c.text for c in batch_chunks]
                
                # 3. Generate embeddings
                embeddings = await provider.get_embeddings(texts)
                
                # Validate vector dimension
                if len(embeddings[0]) != settings.EMBEDDING_DIMENSION:
                    raise ValueError(f"Generated embedding dimension {len(embeddings[0])} does not match configured dimension {settings.EMBEDDING_DIMENSION}")
                
                # 4. Upsert into Qdrant
                points = []
                for chunk, embedding in zip(batch_chunks, embeddings):
                    # Deterministic point ID = PostgreSQL chunk UUID
                    point_id = str(chunk.id)
                    
                    payload = QdrantPayload(
                        document_id=str(doc.id),
                        chunk_id=str(chunk.id),
                        org_id=str(chunk.org_id),
                        filename=doc.filename,
                        page_number=chunk.page_number,
                        section=chunk.section,
                        source_type=chunk.source_type,
                        chunk_index=chunk.chunk_index,
                        content_hash=chunk.content_hash,
                        text=chunk.text
                    ).model_dump()
                    
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload=payload
                        )
                    )
                
                await qdrant.upsert(
                    collection_name="enterprise_knowledge",
                    points=points
                )
                
            # 5. Mark document indexed
            doc.status = "indexed"
            doc.error_message = None
            db.add(doc)
            await db.commit()
            
            # Invalidate BM25 cache for this org
            from app.services.retrieval.bm25 import BM25Manager
            BM25Manager.invalidate_cache(doc.org_id)
            
        except Exception as e:
            await db.rollback()
            try:
                # Refresh doc and mark failed
                doc = await db.get(Document, doc_id)
                if doc:
                    doc.status = "failed"
                    doc.error_message = f"Indexing error: {str(e)}"
                    db.add(doc)
                    await db.commit()
            except:
                pass
