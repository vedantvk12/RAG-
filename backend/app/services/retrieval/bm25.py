from typing import Dict, List, Optional
from uuid import UUID
from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.models import Document, DocumentChunk
from app.db.session import AsyncSessionLocal
from app.schemas.retrieval import RetrievalResult
from app.services.retrieval.tokenizer import tokenize
from app.core.config import settings

class BM25Index:
    def __init__(self, bm25_okapi: BM25Okapi, chunks: List[DocumentChunk], docs: Dict[UUID, Document]):
        self.bm25_okapi = bm25_okapi
        self.chunks = chunks
        self.docs = docs

# In-memory per-tenant BM25 cache
# Structure: { org_id_str: BM25Index }
_bm25_cache: Dict[str, BM25Index] = {}

class BM25Manager:
    """
    Manages building and querying a BM25 index per organization.
    """
    
    @classmethod
    def invalidate_cache(cls, org_id: UUID):
        """Invalidate the cache for a specific organization."""
        org_id_str = str(org_id)
        if org_id_str in _bm25_cache:
            del _bm25_cache[org_id_str]

    @classmethod
    async def _build_index_for_org(cls, org_id: UUID) -> Optional[BM25Index]:
        """Fetch all chunks for an organization and build the index."""
        async with AsyncSessionLocal() as db:
            # Only index chunks from indexed documents
            result = await db.execute(
                select(Document).where(
                    Document.org_id == org_id,
                    Document.status == "indexed"
                )
            )
            docs = result.scalars().all()
            
            if not docs:
                return None
                
            doc_ids = [d.id for d in docs]
            docs_dict = {d.id: d for d in docs}
            
            chunk_result = await db.execute(
                select(DocumentChunk).where(
                    DocumentChunk.doc_id.in_(doc_ids)
                )
            )
            chunks = chunk_result.scalars().all()
            
            if not chunks:
                return None
                
            # Tokenize all chunks
            tokenized_corpus = [tokenize(chunk.text) for chunk in chunks]
            
            bm25_okapi = BM25Okapi(tokenized_corpus)
            index = BM25Index(bm25_okapi=bm25_okapi, chunks=chunks, docs=docs_dict)
            
            _bm25_cache[str(org_id)] = index
            return index

    @classmethod
    async def search(cls, query: str, org_id: UUID, top_k: int = None) -> List[RetrievalResult]:
        """Search the BM25 index for the organization."""
        top_k = top_k or settings.BM25_TOP_K
        org_id_str = str(org_id)
        
        index = _bm25_cache.get(org_id_str)
        if not index:
            index = await cls._build_index_for_org(org_id)
            if not index:
                return []
                
        tokenized_query = tokenize(query)
        # Handle empty query
        if not tokenized_query:
            return []
            
        scores = index.bm25_okapi.get_scores(tokenized_query)
        
        # Combine chunks with scores
        scored_chunks = list(zip(index.chunks, scores))
        # Filter out 0 scores
        scored_chunks = [(c, s) for c, s in scored_chunks if s > 0]
        # Sort descending by score
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Take top K
        top_chunks = scored_chunks[:top_k]
        
        results = []
        for rank, (chunk, score) in enumerate(top_chunks, start=1):
            doc = index.docs.get(chunk.doc_id)
            results.append(RetrievalResult(
                chunk_id=chunk.id,
                document_id=chunk.doc_id,
                org_id=chunk.org_id,
                text=chunk.text,
                filename=doc.filename if doc else "Unknown",
                page_number=chunk.page_number,
                section=chunk.section,
                source_type=chunk.source_type,
                chunk_index=chunk.chunk_index,
                bm25_score=score,
                bm25_rank=rank
            ))
            
        return results
