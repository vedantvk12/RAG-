import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.services.retrieval.fusion import ReciprocalRankFusion
from app.schemas.retrieval import RetrievalResult
from app.core.config import settings
from app.db.qdrant import init_qdrant
import time

client = TestClient(app)

def create_user_and_login(email: str, password: str = "securepassword") -> tuple[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return me_res.json()["id"], token

def create_org(token: str, name: str) -> str:
    res = client.post("/api/v1/organizations/", json={"name": name}, headers={"Authorization": f"Bearer {token}"})
    return res.json()["id"]

def test_rrf_math():
    """Test standard Reciprocal Rank Fusion calculation"""
    org_id = uuid4()
    doc_id = uuid4()
    chunk1 = uuid4()
    chunk2 = uuid4()
    chunk3 = uuid4()

    dense_results = [
        RetrievalResult(chunk_id=chunk1, document_id=doc_id, org_id=org_id, text="A", filename="f", chunk_index=1, dense_score=0.9, dense_rank=1),
        RetrievalResult(chunk_id=chunk2, document_id=doc_id, org_id=org_id, text="B", filename="f", chunk_index=2, dense_score=0.8, dense_rank=2),
    ]

    bm25_results = [
        RetrievalResult(chunk_id=chunk3, document_id=doc_id, org_id=org_id, text="C", filename="f", chunk_index=3, bm25_score=1.5, bm25_rank=1),
        RetrievalResult(chunk_id=chunk1, document_id=doc_id, org_id=org_id, text="A", filename="f", chunk_index=1, bm25_score=1.2, bm25_rank=2),
    ]

    fused = ReciprocalRankFusion.fuse(dense_results, bm25_results, top_k=10)
    
    # chunk1 is rank 1 in Dense, rank 2 in BM25
    # chunk3 is missing in Dense (rank 1000), rank 1 in BM25
    # chunk2 is rank 2 in Dense, missing in BM25 (rank 1000)
    
    # RRF(chunk1) = 1/(60+1) + 1/(60+2)
    # RRF(chunk3) = 1/(60+1000) + 1/(60+1)
    # RRF(chunk2) = 1/(60+2) + 1/(60+1000)
    
    assert len(fused) == 3
    assert fused[0].chunk_id == chunk1
    assert fused[1].chunk_id == chunk3
    assert fused[2].chunk_id == chunk2
    assert fused[0].final_rank == 1

@pytest.fixture(autouse=True)
def mock_fastembed(monkeypatch):
    from app.llm.fastembed_provider import FastEmbedProvider
    async def mock_get_embeddings(self, texts):
        return [[0.1] * settings.EMBEDDING_DIMENSION for _ in texts]
    async def mock_get_embedding(self, text):
        return [0.1] * settings.EMBEDDING_DIMENSION
    
    monkeypatch.setattr(FastEmbedProvider, "get_embeddings", mock_get_embeddings)
    monkeypatch.setattr(FastEmbedProvider, "get_embedding", mock_get_embedding)

@pytest.mark.asyncio
async def test_tenant_isolation_in_retrieval(tmp_path):
    await init_qdrant()
    
    # Setup users and orgs
    userA, tokenA = create_user_and_login(f"searchA_{uuid4()}@example.com")
    orgA = create_org(tokenA, "Org A")
    
    userB, tokenB = create_user_and_login(f"searchB_{uuid4()}@example.com")
    orgB = create_org(tokenB, "Org B")

    # Upload and index doc for A
    fileA = tmp_path / "A.txt"
    fileA.write_text("Organization A uses PostgreSQL for database.")
    resA = client.post(
        f"/api/v1/organizations/{orgA}/documents/",
        files={"file": ("A.txt", open(fileA, "rb"), "text/plain")},
        headers={"Authorization": f"Bearer {tokenA}"}
    )
    docA_id = resA.json()["id"]
    client.post(f"/api/v1/organizations/{orgA}/documents/{docA_id}/index", headers={"Authorization": f"Bearer {tokenA}"})

    # Upload and index doc for B
    fileB = tmp_path / "B.txt"
    fileB.write_text("Organization B uses PostgreSQL for database.")
    resB = client.post(
        f"/api/v1/organizations/{orgB}/documents/",
        files={"file": ("B.txt", open(fileB, "rb"), "text/plain")},
        headers={"Authorization": f"Bearer {tokenB}"}
    )
    docB_id = resB.json()["id"]
    client.post(f"/api/v1/organizations/{orgB}/documents/{docB_id}/index", headers={"Authorization": f"Bearer {tokenB}"})

    # Small delay for background processing (in TestClient this is synchronous but good practice)
    time.sleep(0.5)

    # 1. Search as User A
    res_search_A = client.post(
        "/api/v1/retrieval/search",
        json={"query": "PostgreSQL database"},
        headers={"Authorization": f"Bearer {tokenA}"}
    )
    assert res_search_A.status_code == 200
    results_A = res_search_A.json()["results"]
    assert len(results_A) >= 1
    for r in results_A:
        assert r["org_id"] == orgA
        assert "Organization A" in r["text"]

    # 2. Search as User B
    res_search_B = client.post(
        "/api/v1/retrieval/search",
        json={"query": "PostgreSQL database"},
        headers={"Authorization": f"Bearer {tokenB}"}
    )
    assert res_search_B.status_code == 200
    results_B = res_search_B.json()["results"]
    assert len(results_B) >= 1
    for r in results_B:
        assert r["org_id"] == orgB
        assert "Organization B" in r["text"]
        
    # User B cannot see A's documents, guaranteed.
