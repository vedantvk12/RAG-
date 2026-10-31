from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID
from app.schemas.retrieval import RetrievalResult

class AgentStepPayload(BaseModel):
    sub_query: Optional[str] = None
    retrieved_chunk_ids: Optional[List[str]] = None
    scores: Optional[List[float]] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    refined_query: Optional[str] = None
    iteration: Optional[int] = None
    status: Optional[str] = None
    retrieval_query_count: Optional[int] = None
    llm_call_count: Optional[int] = None
    latency_ms: Optional[float] = None

class AgentState(BaseModel):
    run_id: UUID
    org_id: UUID
    user_id: UUID
    original_query: str
    classification: str = "simple"
    retrieval_plan: List[str] = Field(default_factory=list)
    accumulated_evidence: List[RetrievalResult] = Field(default_factory=list)
    current_iteration: int = 0
    max_iterations: int = 3
    llm_call_count: int = 0
    retrieval_query_count: int = 0
    is_sufficient: bool = False
    final_answer: Optional[str] = None
    status: str = "planning" # planning, retrieving, evaluating, synthesizing, completed, abstained
    logs: List[Dict[str, Any]] = Field(default_factory=list)
