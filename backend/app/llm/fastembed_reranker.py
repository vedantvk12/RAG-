import asyncio
from typing import Any, Dict, List, Optional
from fastembed.rerank.cross_encoder import TextCrossEncoder
from app.llm.provider import RerankerProvider

class FastEmbedReranker(RerankerProvider):
    def __init__(self, model_name: str = "BAAI/bge-reranker-base", batch_size: int = 16):
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None

    def _get_model(self) -> TextCrossEncoder:
        if self._model is None:
            self._model = TextCrossEncoder(model_name=self.model_name)
        return self._model

    def _rerank(self, query: str, documents: List[str], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        if not documents:
            return []

        model = self._get_model()
        
        # fastembed model.rerank for a single query yields an Iterable[float] (or array of floats).
        # We wrap it in a list to consume the generator.
        generator_result = list(model.rerank(query, documents, batch_size=self.batch_size))
        
        # Normalize nested lists if fastembed returns Iterable[Iterable[float]]
        flat_scores = []
        for s in generator_result:
            if hasattr(s, "__iter__") and not isinstance(s, float) and not isinstance(s, int):
                flat_scores.extend(list(s))
            else:
                flat_scores.append(float(s))
                
        results = [
            {"index": i, "score": float(score)}
            for i, score in enumerate(flat_scores)
        ]
        
        # Sort descending by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        if top_k is not None:
            results = results[:top_k]
            
        return results

    async def rerank(self, query: str, documents: List[str], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._rerank, query, documents, top_k)
