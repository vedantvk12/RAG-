from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class DocumentChunkResponse(BaseModel):
    id: UUID
    doc_id: UUID
    org_id: UUID
    chunk_index: int
    text: str
    page_number: Optional[int]
    section: Optional[str]
    source_type: Optional[str]
    
    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: UUID
    org_id: UUID
    uploaded_by: UUID
    filename: str
    status: str
    error_message: Optional[str]
    created_at: datetime
    metadata_json: Optional[Dict[str, Any]]
    content_hash: Optional[str]
    
    class Config:
        from_attributes = True

class DocumentWithChunksResponse(DocumentResponse):
    chunks: Optional[List[DocumentChunkResponse]] = None
    
    class Config:
        from_attributes = True

class DocumentStatusResponse(BaseModel):
    status: str
    error_message: Optional[str]
