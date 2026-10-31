from typing import List
from fastembed import TextEmbedding
import asyncio
from app.llm.provider import EmbeddingProvider
from app.core.config import settings

class FastEmbedProvider(EmbeddingProvider):
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model
    
    async def get_embedding(self, text: str) -> List[float]:
        # fastembed is synchronous but very fast since it uses ONNX runtime, 
        # but to avoid blocking the async event loop for large texts, we run it in a threadpool.
        return (await self.get_embeddings([text]))[0]

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        # Run the synchronous embedding generation in a thread
        def _embed():
            model = self._get_model()
            # embed returns an iterator of numpy arrays
            return [emb.tolist() for emb in model.embed(texts)]
        
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(None, _embed)
        return embeddings
