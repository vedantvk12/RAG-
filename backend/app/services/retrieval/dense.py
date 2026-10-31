import asyncio
from typing import List
from uuid import UUID
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.db.qdrant import get_qdrant_client
from app.llm.fastembed_provider import FastEmbedProvider
from app.schemas.retrieval import RetrievalResult
from app.core.config import settings

# Shared provider
provider = FastEmbedProvider()

class DenseRetriever:
    @classmethod
    async def search(cls, query: str, org_id: UUID, top_k: int = None) -> List[RetrievalResult]:
        """
        Generates query embedding and searches Qdrant.
        Strictly enforces org_id filtering at the Qdrant level.
        """
        if not query.strip():
            return []
            
        top_k = top_k or settings.DENSE_TOP_K
        
        # 1. Generate embedding for query
        query_vector = await provider.get_embedding(query)
        
        # 2. Query Qdrant with tenant filter
        client = get_qdrant_client()
        search_result = await client.search(
            collection_name="enterprise_knowledge",
            query_vector=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="org_id", match=MatchValue(value=str(org_id)))
                ]
            ),
            limit=top_k
        )
        
        # 3. Format results
        results = []
        for rank, hit in enumerate(search_result, start=1):
            p = hit.payload
            results.append(RetrievalResult(
                chunk_id=UUID(p["chunk_id"]),
                document_id=UUID(p["document_id"]),
                org_id=UUID(p["org_id"]),
                text=p["text"],
                filename=p.get("filename", "Unknown"),
                page_number=p.get("page_number"),
                section=p.get("section"),
                source_type=p.get("source_type"),
                chunk_index=p.get("chunk_index", 0),
                dense_score=hit.score,
                dense_rank=rank
            ))
            
        return results
