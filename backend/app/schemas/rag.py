from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID

class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)
    mode: str = Field("deterministic", description="Mode can be deterministic or agentic")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Previous conversation turns for context resolution")

class CitedSource(BaseModel):
    source_id: str
    document_id: UUID
    chunk_id: UUID
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    text: str

class CitationValidation(BaseModel):
    valid_citations: List[str]
    invalid_citations: List[str]

class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[CitedSource]
    retrieval_metadata: Dict[str, Any]
    citation_validation: CitationValidation
