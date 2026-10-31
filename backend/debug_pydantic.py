import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def run_test():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register and login
        await ac.post("/api/v1/auth/register", json={"email": "debug@example.com", "password": "password"})
        login_res = await ac.post("/api/v1/auth/login", data={"username": "debug@example.com", "password": "password"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create org
        org_res = await ac.post("/api/v1/organizations/", json={"name": "Debug Org"}, headers=headers)
        org_id = org_res.json()["id"]

        # Directly insert to DB
        from app.db.session import AsyncSessionLocal
        from app.db.models import AgentRun, AgentStep, Query
        async with AsyncSessionLocal() as db:
            user_res = await ac.get("/api/v1/auth/me", headers=headers)
            user_id = user_res.json()["id"]
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

        # Call endpoint
        res = await ac.get(f"/api/v1/traces?org_id={org_id}", headers=headers)
        print("Status:", res.status_code)
        print("Response:", res.text)

asyncio.run(run_test())
