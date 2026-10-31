from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime
from uuid import UUID

class AgentStepResponse(BaseModel):
    id: UUID
    run_id: UUID
    step_type: str
    latency_ms: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class AgentRunResponse(BaseModel):
    id: UUID
    query_id: Optional[UUID] = None
    org_id: UUID
    user_id: UUID
    original_query: str
    classification: Optional[str] = None
    status: str
    iterations: int
    total_latency_ms: Optional[float] = None
    workflow_trace: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    steps: Optional[List[AgentStepResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class AgentRunSummary(BaseModel):
    id: UUID
    query_id: Optional[UUID] = None
    org_id: UUID
    user_id: UUID
    original_query: str
    classification: Optional[str] = None
    status: str
    iterations: int
    total_latency_ms: Optional[float] = None
    workflow_trace: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AgentRunListResponse(BaseModel):
    items: List[AgentRunSummary]
    total: int
