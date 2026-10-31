from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID

class RetrievalResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    org_id: UUID
    text: str
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    source_type: Optional[str] = None
    chunk_index: int
    
    dense_score: Optional[float] = None
    bm25_score: Optional[float] = None
    dense_rank: Optional[int] = None
    bm25_rank: Optional[int] = None
    rrf_score: Optional[float] = Field(None, description="Reciprocal Rank Fusion score")
    rerank_score: Optional[float] = Field(None, description="Cross-encoder reranking score")
    
    # Final ordering index
    final_rank: Optional[int] = Field(None, description="Final rank after fusion or reranking")

class RetrievalRequest(BaseModel):
    query: str
    top_k: Optional[int] = None

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(10, ge=1, le=100)

class RerankSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=100)

class RetrievalResponse(BaseModel):
    query: str
    results: List[RetrievalResult]
