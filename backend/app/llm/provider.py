from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str
    content: str

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, messages: List[ChatMessage], **kwargs) -> str:
        """Generate a response from the LLM based on the conversation history."""
        pass

    @abstractmethod
    async def stream_response(self, messages: List[ChatMessage], **kwargs):
        """Stream a response from the LLM based on the conversation history."""
        pass

class EmbeddingProvider(ABC):
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Get the embedding vector for a single piece of text."""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embedding vectors for a list of texts."""
        pass

class RerankerProvider(ABC):
    @abstractmethod
    async def rerank(self, query: str, documents: List[str], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Rerank a list of documents based on relevance to the query."""
        pass
