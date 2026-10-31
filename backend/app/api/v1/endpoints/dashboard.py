from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from uuid import UUID

from app.db.session import get_db
from app.db.models import AgentRun, Document, Query as DbQuery, User, Membership
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve aggregated dashboard statistics for an organization.
    Checks tenant isolation via matching org_id and current_user's memberships.
    """
    # Enforce tenant isolation
    result = await db.execute(
        select(Membership).where(
            Membership.org_id == org_id,
            Membership.user_id == current_user.id
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized to access this organization's stats")

    # Document stats
    total_docs_query = select(func.count(Document.id)).where(Document.org_id == org_id)
    indexed_docs_query = select(func.count(Document.id)).where(Document.org_id == org_id, Document.status == 'ready')
    failed_docs_query = select(func.count(Document.id)).where(Document.org_id == org_id, Document.status == 'failed')
    
    total_docs = (await db.execute(total_docs_query)).scalar_one()
    indexed_docs = (await db.execute(indexed_docs_query)).scalar_one()
    failed_docs = (await db.execute(failed_docs_query)).scalar_one()

    # Query stats
    total_queries_query = select(func.count(DbQuery.id)).where(DbQuery.org_id == org_id)
    total_queries = (await db.execute(total_queries_query)).scalar_one()

    # AgentRun stats
    agent_runs_query = select(func.count(AgentRun.id)).where(AgentRun.org_id == org_id)
    agent_runs = (await db.execute(agent_runs_query)).scalar_one()
    
    decisions_query = select(func.count(AgentRun.id)).where(
        AgentRun.org_id == org_id,
        AgentRun.classification.notin_(['general_information', 'simple', 'decision_pending'])
    )
    decisions_count = (await db.execute(decisions_query)).scalar_one()

    avg_latency_query = select(func.avg(AgentRun.total_latency_ms)).where(AgentRun.org_id == org_id)
    avg_latency = (await db.execute(avg_latency_query)).scalar_one()

    return {
        "documents": {
            "total": total_docs,
            "indexed": indexed_docs,
            "failed": failed_docs
        },
        "queries": {
            "total": total_queries
        },
        "agent_runs": {
            "total": agent_runs,
            "decisions": decisions_count,
            "avg_latency_ms": avg_latency if avg_latency else 0.0
        }
    }
