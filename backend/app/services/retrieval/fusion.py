from typing import List, Dict
from uuid import UUID
from app.schemas.retrieval import RetrievalResult
from app.core.config import settings

class ReciprocalRankFusion:
    @classmethod
    def fuse(cls, dense_results: List[RetrievalResult], bm25_results: List[RetrievalResult], top_k: int = None) -> List[RetrievalResult]:
        """
        Implements Reciprocal Rank Fusion to combine Dense and BM25 search results.
        RRF_score = 1 / (RRF_K + rank)
        """
        top_k = top_k or settings.FINAL_TOP_K
        k = settings.RRF_K
        
        # We need a unified dict to track items by chunk_id
        fused_scores: Dict[UUID, float] = {}
        items: Dict[UUID, RetrievalResult] = {}
        
        # 1. Process Dense Results
        for item in dense_results:
            chunk_id = item.chunk_id
            if chunk_id not in items:
                items[chunk_id] = item
            
            rank = item.dense_rank or 1000 # Fallback if missing
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            
        # 2. Process BM25 Results
        for item in bm25_results:
            chunk_id = item.chunk_id
            if chunk_id not in items:
                items[chunk_id] = item
            else:
                # Merge BM25 specific metadata into the existing item
                items[chunk_id].bm25_score = item.bm25_score
                items[chunk_id].bm25_rank = item.bm25_rank
                
            rank = item.bm25_rank or 1000
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            
        # 3. Sort by fused RRF score
        sorted_chunks = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 4. Construct final results
        final_results = []
        for final_rank, (chunk_id, rrf_score) in enumerate(sorted_chunks[:top_k], start=1):
            result = items[chunk_id]
            result.rrf_score = rrf_score
            result.final_rank = final_rank
            final_results.append(result)
            
        return final_results
