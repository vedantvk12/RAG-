from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings

# Global async client
_qdrant_client = None

def get_qdrant_client() -> AsyncQdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
    return _qdrant_client

async def init_qdrant():
    """
    Initialize Qdrant collection if it does not exist.
    Called during app startup.
    """
    client = get_qdrant_client()
    collection_name = "enterprise_knowledge"
    
    # Check if collection exists
    collections = await client.get_collections()
    if not any(c.name == collection_name for c in collections.collections):
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=Distance.COSINE
            )
        )
