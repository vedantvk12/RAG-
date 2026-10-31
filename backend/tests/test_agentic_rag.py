import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.rag import RAGQueryRequest
from app.services.rag.orchestrator import AgenticRAGOrchestrator
from app.schemas.retrieval import RetrievalResult

@pytest.mark.asyncio
async def test_agentic_simple_query_bypass():
    """Test that a simple query avoids unnecessary orchestration and sets classification correctly."""
    orchestrator = AgenticRAGOrchestrator()
    
    # Mock LLM to return simple classification
    orchestrator.llm_provider = AsyncMock()
    orchestrator.llm_provider.generate_response.side_effect = [
        '{"classification": "simple", "sub_queries": []}',
        "This is the final answer [Source 1]"
    ]
    
    # Mock retrieval and reranking
    mock_retrieval_result = RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        org_id=uuid4(),
        text="Mock evidence",
        filename="mock.txt",
        chunk_index=0,
        rerank_score=0.9
    )
    
    with patch("app.services.rag.orchestrator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
        with patch("app.services.rag.orchestrator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
            
            mock_hybrid.return_value = [mock_retrieval_result]
            mock_rerank.return_value = [mock_retrieval_result]
            
            org_id = mock_retrieval_result.org_id
            user_id = uuid4()
            
            with patch("app.services.rag.orchestrator.AsyncSessionLocal") as mock_session:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db
                mock_run = MagicMock()
                mock_run.id = uuid4()
                mock_db.get.return_value = mock_run
                
                response = await orchestrator.run("What is X?", org_id, user_id)
                
                assert response.retrieval_metadata["agentic_classification"] == "simple"
                assert response.retrieval_metadata["agentic_iterations"] == 1
                # 1 call for plan, 0 for evaluate (bypassed), 1 for synthesize
                assert response.retrieval_metadata["agentic_llm_calls"] == 2
                assert response.answer == "This is the final answer [Source 1]"

@pytest.mark.asyncio
async def test_agentic_tenant_isolation():
    """Test that tenant isolation is strictly enforced."""
    orchestrator = AgenticRAGOrchestrator()
    orchestrator.llm_provider = AsyncMock()
    orchestrator.llm_provider.generate_response.return_value = '{"classification": "simple"}'
    
    org_id = uuid4()
    malicious_org_id = uuid4()
    
    mock_retrieval_result = RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        org_id=malicious_org_id,
        text="Mock evidence",
        filename="mock.txt",
        chunk_index=0
    )
    
    with patch("app.services.rag.orchestrator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
        with patch("app.services.rag.orchestrator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
            mock_hybrid.return_value = [mock_retrieval_result]
            mock_rerank.return_value = [mock_retrieval_result]
            
            with patch("app.services.rag.orchestrator.AsyncSessionLocal") as mock_session:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db
                
                with pytest.raises(Exception, match="Security Error"):
                    await orchestrator.run("Secret data?", org_id, uuid4())

@pytest.mark.asyncio
async def test_agentic_max_iterations():
    """Test that agent respects MAX_AGENT_ITERATIONS and stops."""
    orchestrator = AgenticRAGOrchestrator()
    orchestrator.llm_provider = AsyncMock()
    
    orchestrator.llm_provider.generate_response.side_effect = [
        '{"classification": "multi-hop", "sub_queries": ["What is X?"]}', # classify
        '{"is_sufficient": false, "reason": "missing"}', # eval 1
        "Refined query 1", # refine 1
        '{"is_sufficient": false, "reason": "missing"}', # eval 2
        "Refined query 2", # refine 2
        '{"is_sufficient": false, "reason": "missing"}', # eval 3
        "This is the final best effort answer [Source 1]" # synthesize
    ]
    
    org_id = uuid4()
    mock_retrieval_result = RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        org_id=org_id,
        text="Mock evidence",
        filename="mock.txt",
        chunk_index=0,
        rerank_score=0.01 
    )
    
    with patch("app.services.rag.orchestrator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
        with patch("app.services.rag.orchestrator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
            with patch("app.services.rag.orchestrator.MAX_AGENT_LLM_CALLS", 10):
                mock_hybrid.return_value = [mock_retrieval_result]
                mock_rerank.return_value = [mock_retrieval_result]
                
                with patch("app.services.rag.orchestrator.AsyncSessionLocal") as mock_session:
                    mock_db = AsyncMock()
                    mock_session.return_value.__aenter__.return_value = mock_db
                    mock_run = MagicMock()
                    mock_run.id = uuid4()
                    mock_db.get.return_value = mock_run
                    
                    response = await orchestrator.run("Compare X and Y?", org_id, uuid4())
                    
                    assert response.retrieval_metadata["agentic_iterations"] == 3
                    assert response.answer == "This is the final best effort answer [Source 1]"

@pytest.mark.asyncio
async def test_agentic_max_llm_calls():
    """Test that agent respects MAX_AGENT_LLM_CALLS."""
    orchestrator = AgenticRAGOrchestrator()
    orchestrator.llm_provider = AsyncMock()
    
    # We will just return sufficient=false until it hits the max LLM calls
    def mock_llm_response(*args, **kwargs):
        # Determine if it's classification prompt or evaluation prompt
        msg = args[0][0].content
        if "classify it" in msg:
            return '{"classification": "multi-hop", "sub_queries": ["X"]}'
        return '{"is_sufficient": false, "reason": "missing"}'
        
    orchestrator.llm_provider.generate_response.side_effect = mock_llm_response
    
    org_id = uuid4()
    mock_retrieval_result = RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        org_id=org_id,
        text="Mock evidence",
        filename="mock.txt",
        chunk_index=0,
        rerank_score=0.01 
    )
    
    with patch("app.services.rag.orchestrator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
        with patch("app.services.rag.orchestrator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
            mock_hybrid.return_value = [mock_retrieval_result]
            mock_rerank.return_value = [mock_retrieval_result]
            
            with patch("app.services.rag.orchestrator.AsyncSessionLocal") as mock_session:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db
                mock_run = MagicMock()
                mock_run.id = uuid4()
                mock_db.get.return_value = mock_run
                
                # Should hit the limit and abstain
                response = await orchestrator.run("Test Max LLM?", org_id, uuid4())
                
                # We expect LLM calls to hit the limit (5) and then abort the loop safely
                assert response.retrieval_metadata["agentic_llm_calls"] == 5
                assert "do not contain enough information" in response.answer

@pytest.mark.asyncio
async def test_agentic_abstain_no_evidence():
    """Test that agent abstains when no evidence is found."""
    orchestrator = AgenticRAGOrchestrator()
    orchestrator.llm_provider = AsyncMock()
    orchestrator.llm_provider.generate_response.side_effect = [
        '{"classification": "multi-hop", "sub_queries": ["What is X?"]}', # classify
        # Since no evidence is found, the agent sets is_sufficient = False directly without LLM call
        "Refined query 1", # refine 1
        "Refined query 2", # refine 2
        "Refined query 3", # refine 3 (hits max iter)
        "This shouldn't be reached" # synthesize fallback
    ]
    
    org_id = uuid4()
    
    with patch("app.services.rag.orchestrator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
        with patch("app.services.rag.orchestrator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
            # Return no results
            mock_hybrid.return_value = []
            mock_rerank.return_value = []
            
            with patch("app.services.rag.orchestrator.AsyncSessionLocal") as mock_session:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db
                mock_run = MagicMock()
                mock_run.id = uuid4()
                mock_db.get.return_value = mock_run
                
                response = await orchestrator.run("Unknown data?", org_id, uuid4())
                assert "do not contain enough information" in response.answer

@pytest.mark.asyncio
async def test_agentic_latency_enforcement():
    """Test that agent respects MAX_AGENT_LATENCY_SECONDS."""
    orchestrator = AgenticRAGOrchestrator()
    orchestrator.llm_provider = AsyncMock()
    orchestrator.llm_provider.generate_response.return_value = '{"classification": "simple"}'
    
    org_id = uuid4()
    
    with patch("app.services.rag.orchestrator.time.monotonic") as mock_time:
        # Simulate time passing very fast to hit the 30s timeout immediately after classify
        def time_generator():
            yield 0
            yield 0
            while True:
                yield 31.0
                
        mock_time.side_effect = time_generator()
        
        with patch("app.services.rag.orchestrator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
            with patch("app.services.rag.orchestrator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
                mock_hybrid.return_value = []
                mock_rerank.return_value = []
                
                with patch("app.services.rag.orchestrator.AsyncSessionLocal") as mock_session:
                    mock_db = AsyncMock()
                    mock_session.return_value.__aenter__.return_value = mock_db
                    mock_run = MagicMock()
                    mock_run.id = uuid4()
                    mock_db.get.return_value = mock_run
                    
                    response = await orchestrator.run("Timeout test?", org_id, uuid4())
                    
                    assert "do not contain enough information" in response.answer
