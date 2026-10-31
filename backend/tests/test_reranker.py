import pytest
from uuid import uuid4
import asyncio

from app.schemas.retrieval import RetrievalResult
from app.services.retrieval.reranker import CrossEncoderReranker
from app.llm.provider import RerankerProvider

class MockRerankerProvider(RerankerProvider):
    async def rerank(self, query: str, documents: list[str], top_k: int = None):
        # Deterministic mock: scores based on length of document (longer = higher score for testing sorting)
        # Reverses the order just to prove it does something.
        results = [{"index": i, "score": float(len(d))} for i, d in enumerate(documents)]
        results.sort(key=lambda x: x["score"], reverse=True)
        if top_k is not None:
            results = results[:top_k]
        return results

@pytest.fixture
def mock_reranker():
    provider = MockRerankerProvider()
    return CrossEncoderReranker(provider)

def create_candidate(org_id, text, idx=0):
    return RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        org_id=org_id,
        text=text,
        filename="test.txt",
        chunk_index=idx,
        dense_score=0.5,
        bm25_score=0.5,
        dense_rank=1,
        bm25_rank=1,
        rrf_score=1.0,
        final_rank=idx
    )

@pytest.mark.asyncio
async def test_tenant_isolation_defensive_rejection(mock_reranker):
    org_a = uuid4()
    org_b = uuid4()
    
    candidates = [
        create_candidate(org_a, "Valid for Org A", 1),
        create_candidate(org_b, "Invalid for Org A", 2),
        create_candidate(org_a, "Also valid for Org A", 3)
    ]
    
    # Reranking with context org_a should ignore org_b's candidate
    results = await mock_reranker.rerank_results("query", candidates, org_a, top_k=5)
    
    assert len(results) == 2
    assert all(c.org_id == org_a for c in results)

@pytest.mark.asyncio
async def test_reranker_sorting_and_metadata_preservation(mock_reranker):
    org_id = uuid4()
    candidates = [
        create_candidate(org_id, "Short", 1),
        create_candidate(org_id, "A much longer string that will score higher", 2),
        create_candidate(org_id, "Medium len", 3)
    ]
    
    results = await mock_reranker.rerank_results("query", candidates, org_id, top_k=5)
    
    assert len(results) == 3
    # Based on our mock, the longest string should be first
    assert results[0].text == "A much longer string that will score higher"
    assert results[0].rerank_score == len(results[0].text)
    assert results[0].final_rank == 1
    
    assert results[1].text == "Medium len"
    assert results[1].final_rank == 2
    
    assert results[2].text == "Short"
    assert results[2].final_rank == 3
    
    # Ensure metadata is preserved
    assert results[0].chunk_id == candidates[1].chunk_id

@pytest.mark.asyncio
async def test_reranker_top_k(mock_reranker):
    org_id = uuid4()
    candidates = [create_candidate(org_id, f"Text {i}", i) for i in range(10)]
    
    results = await mock_reranker.rerank_results("query", candidates, org_id, top_k=3)
    
    assert len(results) == 3
