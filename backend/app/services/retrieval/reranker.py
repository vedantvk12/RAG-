from typing import List
from uuid import UUID
import logging

from app.schemas.retrieval import RetrievalResult
from app.llm.fastembed_reranker import FastEmbedReranker

logger = logging.getLogger(__name__)

class CrossEncoderReranker:
    def __init__(self, provider: FastEmbedReranker):
        self.provider = provider

    async def rerank_results(
        self, 
        query: str, 
        candidates: List[RetrievalResult], 
        org_id: UUID,
        top_k: int
    ) -> List[RetrievalResult]:
        """
        Rerank hybrid candidates using a cross-encoder.
        Strictly enforces tenant isolation: rejects candidates not matching org_id.
        """
        if not candidates:
            return []

        # Defensive validation: verify all candidates belong to the authorized org
        valid_candidates = []
        for candidate in candidates:
            if candidate.org_id != org_id:
                logger.error(f"SECURITY WARNING: Candidate chunk {candidate.chunk_id} (org: {candidate.org_id}) rejected for user context org {org_id}.")
                continue
            valid_candidates.append(candidate)

        if not valid_candidates:
            return []

        # Extract texts for the reranker
        documents = [c.text for c in valid_candidates]

        # Rerank
        try:
            # Returns sorted [{"index": int, "score": float}, ...]
            reranked_scores = await self.provider.rerank(query, documents)
        except Exception as e:
            logger.error(f"Reranking failed, falling back to original order: {e}")
            # Fallback to original order if reranker fails (e.g. model failed to load)
            for i, c in enumerate(valid_candidates):
                c.rerank_score = None
                c.final_rank = i + 1
            return valid_candidates[:top_k]

        # Separate targeted candidates (page-targeted or overview) from generic search candidates
        targeted = [c for c in valid_candidates if getattr(c, 'rerank_score', 0) in [1.0, 0.95]]
        
        # Apply scores and new ranks
        final_results = []
        for rank, score_dict in enumerate(reranked_scores, start=1):
            original_idx = score_dict["index"]
            candidate = valid_candidates[original_idx]
            
            # Update scores and rank
            candidate.rerank_score = score_dict["score"]
            candidate.final_rank = rank
            if candidate not in targeted:
                final_results.append(candidate)

        merged = targeted + [c for c in final_results if c.chunk_id not in {t.chunk_id for t in targeted}]
        return merged[:top_k]

# Singleton instance
reranker_provider = FastEmbedReranker()
reranker_service = CrossEncoderReranker(provider=reranker_provider)
