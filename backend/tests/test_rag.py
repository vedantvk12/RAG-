import pytest
from uuid import uuid4
import asyncio

from app.schemas.retrieval import RetrievalResult
from app.schemas.rag import RAGQueryRequest
from app.services.rag.generator import RAGGenerator
from app.llm.provider import LLMProvider, ChatMessage

class MockLLMProvider(LLMProvider):
    def __init__(self, answer: str = "This is a mock answer based on [Source 1]."):
        self.answer = answer
        self.called = False

    async def generate_response(self, messages: list[ChatMessage], **kwargs) -> str:
        self.called = True
        return self.answer
        
    async def stream_response(self, messages, **kwargs):
        pass

@pytest.fixture
def mock_rag_generator():
    generator = RAGGenerator()
    generator.llm_provider = MockLLMProvider()
    return generator

def create_candidate(org_id, text, idx=1):
    return RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        org_id=org_id,
        text=text,
        filename="test.txt",
        chunk_index=idx,
        dense_score=0.9,
        bm25_score=0.9,
        dense_rank=1,
        bm25_rank=1,
        rrf_score=1.0,
        final_rank=idx,
        rerank_score=0.95
    )

@pytest.mark.asyncio
async def test_rag_tenant_isolation_defensive_rejection(mock_rag_generator, monkeypatch):
    org_a = uuid4()
    org_b = uuid4()
    
    # We must patch HybridRetriever and Reranker to mock retrieval returning an unauthorized chunk
    async def mock_hybrid(*args, **kwargs):
        return [create_candidate(org_a, "valid"), create_candidate(org_b, "invalid")]
        
    async def mock_rerank(*args, **kwargs):
        return [create_candidate(org_a, "valid"), create_candidate(org_b, "invalid")]
        
    monkeypatch.setattr("app.services.rag.generator.HybridRetriever.search", mock_hybrid)
    monkeypatch.setattr("app.services.rag.generator.reranker_service.rerank_results", mock_rerank)
    
    with pytest.raises(Exception) as exc:
        await mock_rag_generator.generate_grounded_response("test", org_a, 5)
        
    assert "Security Error" in str(exc.value)
    assert not mock_rag_generator.llm_provider.called

@pytest.mark.asyncio
async def test_rag_abstention_no_results(mock_rag_generator, monkeypatch):
    org_a = uuid4()
    
    async def mock_hybrid(*args, **kwargs):
        return []
        
    async def mock_rerank(*args, **kwargs):
        return []
        
    monkeypatch.setattr("app.services.rag.generator.HybridRetriever.search", mock_hybrid)
    monkeypatch.setattr("app.services.rag.generator.reranker_service.rerank_results", mock_rerank)
    
    response = await mock_rag_generator.generate_grounded_response("test", org_a, 5)
    
    assert "available documents do not contain enough information" in response.answer
    assert not mock_rag_generator.llm_provider.called
    assert len(response.sources) == 0

@pytest.mark.asyncio
async def test_rag_citation_validation(mock_rag_generator, monkeypatch):
    org_a = uuid4()
    
    async def mock_hybrid(*args, **kwargs):
        return [create_candidate(org_a, "evidence 1")]
        
    async def mock_rerank(*args, **kwargs):
        return [create_candidate(org_a, "evidence 1")]
        
    monkeypatch.setattr("app.services.rag.generator.HybridRetriever.search", mock_hybrid)
    monkeypatch.setattr("app.services.rag.generator.reranker_service.rerank_results", mock_rerank)
    
    # LLM returning valid and invalid citation
    mock_rag_generator.llm_provider = MockLLMProvider(answer="Valid [Source 1] and Invalid [Source 99]")
    
    response = await mock_rag_generator.generate_grounded_response("test", org_a, 5)
    
    assert mock_rag_generator.llm_provider.called
    assert len(response.sources) == 1
    assert "[Source 1]" in response.citation_validation.valid_citations
    assert "[Source 99]" in response.citation_validation.invalid_citations
