from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, root_validator
from uuid import UUID
from app.schemas.rag import CitedSource

class DecisionRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)

class DecisionConflict(BaseModel):
    claim_a: str
    source_a: str
    claim_b: str
    source_b: str
    unresolved: bool = True

class DecisionFactor(BaseModel):
    description: str
    source_id: str
    evidence_snippet: str

class DecisionRisk(BaseModel):
    description: str
    severity: str
    likelihood: Optional[str] = None
    mitigation: Optional[str] = None
    source_id: str
    evidence_snippet: str

class DecisionImpact(BaseModel):
    description: str
    affected_area: str
    source_id: str
    evidence_snippet: str

class DecisionAlternative(BaseModel):
    name: str
    description: str
    source_id: str
    evidence_snippet: str

class MatrixCriterion(BaseModel):
    name: str
    weight: float = Field(..., ge=0)

class MatrixScore(BaseModel):
    criterion: str
    option: str
    evidence_snippet: str
    source_id: str
    categorical_assessment: str # High, Medium, Low
    numeric_score: float
    weight: float
    weighted_score: float

class DecisionTrace(BaseModel):
    run_id: UUID
    iterations: int
    llm_calls: int
    retrieval_queries: int
    latency_ms: float
    evidence_count: int
    document_count: int

class DecisionResponseBase(BaseModel):
    decision_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    conflicts: List[DecisionConflict] = Field(default_factory=list)
    sources: List[CitedSource] = Field(default_factory=list)
    decision_trace: DecisionTrace

class ComparisonResponse(DecisionResponseBase):
    decision_type: str = "comparison"
    similarities: List[DecisionFactor]
    differences: List[DecisionFactor]
    advantages: List[DecisionFactor]
    disadvantages: List[DecisionFactor]

class RecommendationResponse(DecisionResponseBase):
    decision_type: str = "recommendation"
    recommendation: str
    reasoning: str
    factors: List[DecisionFactor]
    alternatives: List[DecisionAlternative]

class RiskAnalysisResponse(DecisionResponseBase):
    decision_type: str = "risk_analysis"
    risks: List[DecisionRisk]

class ImpactAnalysisResponse(DecisionResponseBase):
    decision_type: str = "impact_analysis"
    impacts: List[DecisionImpact]
    dependencies: List[DecisionFactor]

class DecisionMatrixResponse(DecisionResponseBase):
    decision_type: str = "decision_matrix"
    criteria: List[MatrixCriterion]
    scores: List[MatrixScore]
    total_scores: Dict[str, float] # option -> total score

class GeneralInformationResponse(DecisionResponseBase):
    decision_type: str = "general_information"
    answer: str

class AbstainDecisionResponse(DecisionResponseBase):
    decision_type: str = "abstained"
    reason: str
