from typing import Optional
from pydantic import BaseModel

class QdrantPayload(BaseModel):
    document_id: str
    chunk_id: str
    org_id: str
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    source_type: Optional[str] = None
    chunk_index: int = 0
    content_hash: str
    text: str
