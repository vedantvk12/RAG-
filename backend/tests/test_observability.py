import pytest
import asyncio
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.db.session import AsyncSessionLocal
from app.db.models import AgentRun, AgentStep, Organization, Membership, Query, User
from app.core.security import get_password_hash

client = TestClient(app)

def create_user_and_login(email: str, password: str = "securepassword") -> tuple[str, str]:
    res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    if res.status_code == 400:
        pass
    else:
        assert res.status_code == 201
        
    login_res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return me_res.json()["id"], token

async def async_setup_db_trace(user_id: str, org_id: str):
    async with AsyncSessionLocal() as db:
        # Create a query
        q = Query(user_id=user_id, org_id=org_id, query_text="Obv query")
        db.add(q)
        await db.flush()

        run = AgentRun(
            query_id=q.id,
            org_id=org_id,
            user_id=user_id,
            original_query="Obv query",
            classification="simple",
            status="completed",
            iterations=1,
            total_latency_ms=150.0,
            workflow_trace={"data": "test"}
        )
        db.add(run)
        await db.flush()

        step = AgentStep(
            run_id=run.id,
            step_type="planning",
            latency_ms=75.0,
            payload={"step": 1}
        )
        db.add(step)
        await db.commit()
        return str(run.id)

def setup_org_and_trace(user_id: str, token: str) -> tuple[str, str]:
    org_res = client.post(
        "/api/v1/organizations/",
        json={"name": "Test Org Obv"},
        headers={"Authorization": f"Bearer {token}"}
    )
    org_id = org_res.json()["id"]

    run_id = asyncio.run(async_setup_db_trace(user_id, org_id))
    return org_id, run_id

def test_get_traces_and_stats():
    user_id, token = create_user_and_login("obv@example.com")
    org_id, run_id = setup_org_and_trace(user_id, token)

    # 1. Test get traces
    res = client.get(f"/api/v1/traces?org_id={org_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    
    # 2. Test get specific trace
    res_trace = client.get(f"/api/v1/traces/{run_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_trace.status_code == 200
    trace_data = res_trace.json()
    assert trace_data["id"] == run_id
    assert "steps" in trace_data
    assert len(trace_data["steps"]) >= 1
    
    # 3. Test dashboard stats
    res_stats = client.get(f"/api/v1/dashboard/stats?org_id={org_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert "documents" in stats_data
    assert "queries" in stats_data
    assert "agent_runs" in stats_data
    assert stats_data["agent_runs"]["total"] >= 1
    assert stats_data["queries"]["total"] >= 1

def test_tenant_isolation_traces():
    # User 1
    user1_id, token1 = create_user_and_login("obv1@example.com")
    org1_id, _ = setup_org_and_trace(user1_id, token1)
    
    # User 2
    user2_id, token2 = create_user_and_login("obv2@example.com")
    
    # User 2 tries to access Org 1 traces
    res = client.get(f"/api/v1/traces?org_id={org1_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res.status_code == 403
    
    # User 2 tries to access Org 1 dashboard stats
    res = client.get(f"/api/v1/dashboard/stats?org_id={org1_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res.status_code == 403
