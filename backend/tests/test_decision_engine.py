import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.schemas.decision import (
    DecisionRequest, DecisionResponseBase, ComparisonResponse, 
    DecisionMatrixResponse, RecommendationResponse, AbstainDecisionResponse, GeneralInformationResponse
)
from app.services.decisions.engine import DecisionIntelligenceEngine
from app.schemas.retrieval import RetrievalResult
from app.schemas.rag import CitedSource
from app.schemas.agent import AgentState
from app.services.rag.orchestrator import AgenticRAGOrchestrator

@pytest.fixture
def decision_engine():
    return DecisionIntelligenceEngine()

@pytest.mark.asyncio
async def test_decision_simple_query_bypass(decision_engine):
    """Test that general_information queries bypass decision logic."""
    org_id = uuid4()
    user_id = uuid4()
    
    with patch("app.services.decisions.engine.agentic_orchestrator._safe_llm_call", new_callable=AsyncMock) as mock_llm:
        # LLM classifies as general_information
        mock_llm.return_value = '{"decision_type": "general_information"}'
        
        with patch("app.services.decisions.engine.agentic_orchestrator.run", new_callable=AsyncMock) as mock_rag_run:
            mock_rag_response = MagicMock()
            mock_rag_response.answer = "Simple answer"
            mock_rag_response.sources = []
            mock_rag_response.retrieval_metadata = {"agentic_iterations": 1, "agentic_llm_calls": 2, "agentic_retrieval_queries": 1}
            mock_rag_run.return_value = mock_rag_response
            
            with patch("app.services.decisions.engine.AsyncSessionLocal") as mock_session:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db
                mock_run = MagicMock()
                mock_run.id = uuid4()
                mock_db.get.return_value = mock_run
                
                response = await decision_engine.analyze("What is the capital of France?", org_id, user_id)
                
                assert isinstance(response, GeneralInformationResponse)
                assert response.decision_type == "general_information"
                assert response.answer == "Simple answer"
                assert response.decision_trace.llm_calls == 2

@pytest.mark.asyncio
async def test_decision_comparison(decision_engine):
    """Test full comparison decision type."""
    org_id = uuid4()
    user_id = uuid4()
    
    # Mock classifier
    with patch.object(decision_engine, "_classify_decision_type", new_callable=AsyncMock) as mock_classify:
        mock_classify.return_value = "comparison"
        
        # Mock retrieval
        mock_retrieval_result = RetrievalResult(
            chunk_id=uuid4(), document_id=uuid4(), org_id=org_id, text="Option A is faster. Option B is cheaper.", 
            filename="docs.txt", chunk_index=0, rerank_score=0.9
        )
        
        with patch("app.services.decisions.engine.agentic_orchestrator._retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = [mock_retrieval_result]
            
            with patch("app.services.decisions.engine.analyzers.detect_conflicts", new_callable=AsyncMock) as mock_conflicts:
                mock_conflicts.return_value = []
                
                with patch("app.services.decisions.engine.analyzers.analyze_comparison", new_callable=AsyncMock) as mock_compare:
                    mock_compare.return_value = (
                        [], # sims
                        [], # diffs
                        [], # advs
                        []  # disadvs
                    )
                    
                    with patch("app.services.decisions.engine.AsyncSessionLocal") as mock_session:
                        mock_db = AsyncMock()
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_run = MagicMock()
                        mock_db.get.return_value = mock_run
                        
                        response = await decision_engine.analyze("Compare A and B", org_id, user_id)
                        
                        assert isinstance(response, ComparisonResponse)
                        assert response.decision_type == "comparison"
                        assert response.confidence > 0.0

@pytest.mark.asyncio
async def test_decision_matrix_deterministic_math(decision_engine):
    """Test that matrix math is done purely in Python based on categories."""
    # This directly tests the calculate_matrix function in Analyzers
    from app.services.decisions.analyzers import analyzers
    
    with patch.object(analyzers.llm_provider, "generate_response", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = json.dumps({
            "criteria": [
                {"name": "Cost", "weight": 0.6},
                {"name": "Speed", "weight": 0.4}
            ],
            "assessments": [
                {"criterion": "Cost", "option": "Option A", "assessment": "High", "source_id": "1"}, # Cost high score = 3
                {"criterion": "Speed", "option": "Option A", "assessment": "Low", "source_id": "1"}  # Speed low score = 1
            ]
        })
        
        criteria, scores, total_scores = await analyzers.calculate_matrix("test query", "context")
        
        assert len(criteria) == 2
        # Math: Cost (0.6) * High(3) + Speed (0.4) * Low(1) = 1.8 + 0.4 = 2.2
        assert abs(total_scores["Option A"] - 2.2) < 0.001
        
        assert abs(scores[0].weighted_score - 1.8) < 0.001
        assert abs(scores[1].weighted_score - 0.4) < 0.001

@pytest.mark.asyncio
async def test_decision_tenant_isolation(decision_engine):
    """Test that decision engine strictly isolates tenant data in retrieval."""
    org_id = uuid4()
    malicious_org_id = uuid4()
    
    # We test this by invoking the underlying agentic orchestrator's _retrieve which throws the exception
    from app.services.rag.orchestrator import agentic_orchestrator
    
    mock_retrieval_result = RetrievalResult(
        chunk_id=uuid4(), document_id=uuid4(), org_id=malicious_org_id, 
        text="Mock evidence", filename="mock.txt", chunk_index=0
    )
    
    with patch("app.services.rag.orchestrator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
        with patch("app.services.rag.orchestrator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
            mock_hybrid.return_value = [mock_retrieval_result]
            mock_rerank.return_value = [mock_retrieval_result]
            
            with pytest.raises(Exception, match="Security Error"):
                await agentic_orchestrator._retrieve("Secret data?", org_id, top_k=5)

@pytest.mark.asyncio
async def test_decision_insufficient_evidence_abstain(decision_engine):
    """Test that engine abstains safely when no evidence is found."""
    org_id = uuid4()
    user_id = uuid4()
    
    with patch.object(decision_engine, "_classify_decision_type", new_callable=AsyncMock) as mock_classify:
        mock_classify.return_value = "recommendation"
        
        # Mock retrieval returning empty list
        with patch("app.services.decisions.engine.agentic_orchestrator._retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = []
            
            with patch("app.services.decisions.engine.AsyncSessionLocal") as mock_session:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db
                mock_run = MagicMock()
                mock_db.get.return_value = mock_run
                
                response = await decision_engine.analyze("Recommend a policy.", org_id, user_id)
                
                assert isinstance(response, AbstainDecisionResponse)
                assert response.decision_type == "abstained"
                assert "No evidence retrieved" in response.reason
