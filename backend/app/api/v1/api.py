from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

from app.api.v1.endpoints import auth, organizations, documents, retrieval, rag, decisions, traces, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(documents.router, prefix="/organizations/{org_id}/documents", tags=["documents"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(traces.router, prefix="/traces", tags=["traces"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

@api_router.get("/health/")
async def health_check():
    return {"status": "ok", "message": "API is running"}

@api_router.get("/db-health/")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}
