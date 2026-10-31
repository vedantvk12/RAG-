import pytest
import time
from uuid import uuid4
from fastapi.testclient import TestClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.main import app
from app.core.config import settings
from app.llm.fastembed_provider import FastEmbedProvider
from app.db.qdrant import get_qdrant_client, init_qdrant

client = TestClient(app)

def create_user_and_login(email: str, password: str = "securepassword") -> tuple[str, str]:
    res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return me_res.json()["id"], token

def create_org(token: str, name: str) -> str:
    res = client.post("/api/v1/organizations/", json={"name": name}, headers={"Authorization": f"Bearer {token}"})
    return res.json()["id"]

@pytest.fixture(autouse=True)
def mock_fastembed(monkeypatch):
    async def mock_get_embeddings(self, texts):
        return [[0.1] * settings.EMBEDDING_DIMENSION for _ in texts]
    async def mock_get_embedding(self, text):
        return [0.1] * settings.EMBEDDING_DIMENSION
    
    monkeypatch.setattr(FastEmbedProvider, "get_embeddings", mock_get_embeddings)
    monkeypatch.setattr(FastEmbedProvider, "get_embedding", mock_get_embedding)

@pytest.mark.asyncio
async def test_fastembed_provider():
    provider = FastEmbedProvider()
    # Eager initialization is mocked out or we can just mock the methods
    texts = ["Hello world", "Test embedding"]
    embeddings = await provider.get_embeddings(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == settings.EMBEDDING_DIMENSION
    assert len(embeddings[1]) == settings.EMBEDDING_DIMENSION

@pytest.mark.asyncio
async def test_indexing_pipeline_and_tenant_isolation(tmp_path):
    # Initialize Qdrant collection
    await init_qdrant()
    
    # Setup organizations
    userA_id, tokenA = create_user_and_login(f"tenantA_{uuid4()}@example.com")
    orgA_id = create_org(tokenA, "Org A")
    
    userB_id, tokenB = create_user_and_login(f"tenantB_{uuid4()}@example.com")
    orgB_id = create_org(tokenB, "Org B")

    # Upload doc for A
    fileA = tmp_path / "A.txt"
    fileA.write_text("Organization A secret document")
    resA = client.post(
        f"/api/v1/organizations/{orgA_id}/documents/",
        files={"file": ("A.txt", open(fileA, "rb"), "text/plain")},
        headers={"Authorization": f"Bearer {tokenA}"}
    )
    docA_id = resA.json()["id"]

    # Upload doc for B
    fileB = tmp_path / "B.txt"
    fileB.write_text("Organization B confidential file")
    resB = client.post(
        f"/api/v1/organizations/{orgB_id}/documents/",
        files={"file": ("B.txt", open(fileB, "rb"), "text/plain")},
        headers={"Authorization": f"Bearer {tokenB}"}
    )
    docB_id = resB.json()["id"]

    # Ensure parsing is complete (synchronous in TestClient due to BackgroundTasks executing immediately)
    
    # 1. Cross-tenant authorization failure
    res_b_index_a = client.post(
        f"/api/v1/organizations/{orgA_id}/documents/{docA_id}/index",
        headers={"Authorization": f"Bearer {tokenB}"}
    )
    assert res_b_index_a.status_code == 403

    # 2. Trigger Indexing for A
    res_index_a = client.post(
        f"/api/v1/organizations/{orgA_id}/documents/{docA_id}/index",
        headers={"Authorization": f"Bearer {tokenA}"}
    )
    assert res_index_a.status_code == 202

    # 3. Trigger Indexing for B
    res_index_b = client.post(
        f"/api/v1/organizations/{orgB_id}/documents/{docB_id}/index",
        headers={"Authorization": f"Bearer {tokenB}"}
    )
    assert res_index_b.status_code == 202
    
    # Wait for status to be "indexed"
    time.sleep(1) # just in case
    
    status_a = client.get(
        f"/api/v1/organizations/{orgA_id}/documents/{docA_id}/index-status",
        headers={"Authorization": f"Bearer {tokenA}"}
    ).json()
    assert status_a["status"] == "indexed"
    
    status_b = client.get(
        f"/api/v1/organizations/{orgB_id}/documents/{docB_id}/index-status",
        headers={"Authorization": f"Bearer {tokenB}"}
    ).json()
    assert status_b["status"] == "indexed"

    # 4. Verify in Qdrant & Tenant Isolation
    qdrant = get_qdrant_client()
    
    # Fetch all points for Org A
    res_qdrant_a = await qdrant.scroll(
        collection_name="enterprise_knowledge",
        scroll_filter=Filter(
            must=[FieldCondition(key="org_id", match=MatchValue(value=orgA_id))]
        )
    )
    points_a = res_qdrant_a[0]
    assert len(points_a) >= 1
    for p in points_a:
        assert p.payload["org_id"] == orgA_id
        assert p.payload["document_id"] == docA_id
        assert "Organization A" in p.payload["text"]

    # Fetch all points for Org B
    res_qdrant_b = await qdrant.scroll(
        collection_name="enterprise_knowledge",
        scroll_filter=Filter(
            must=[FieldCondition(key="org_id", match=MatchValue(value=orgB_id))]
        )
    )
    points_b = res_qdrant_b[0]
    assert len(points_b) >= 1
    for p in points_b:
        assert p.payload["org_id"] == orgB_id
        assert p.payload["document_id"] == docB_id
        assert "Organization B" in p.payload["text"]

    # 5. Verify Idempotency
    # Re-index A
    client.post(
        f"/api/v1/organizations/{orgA_id}/documents/{docA_id}/index",
        headers={"Authorization": f"Bearer {tokenA}"}
    )
    
    # Check if duplicate vectors exist
    res_qdrant_a_after = await qdrant.scroll(
        collection_name="enterprise_knowledge",
        scroll_filter=Filter(
            must=[FieldCondition(key="org_id", match=MatchValue(value=orgA_id))]
        )
    )
    assert len(res_qdrant_a_after[0]) == len(points_a) # No duplicates
