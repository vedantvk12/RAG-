from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.db.session import get_db
from app.db.models import AgentRun, AgentStep, User
from app.schemas.trace import AgentRunResponse, AgentRunListResponse, AgentStepResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=AgentRunListResponse)
async def get_traces(
    org_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve agent runs for the organization.
    Checks tenant isolation via matching org_id and current_user's memberships.
    """
    # Enforce tenant isolation
    from app.db.models import Membership
    result = await db.execute(
        select(Membership).where(
            Membership.org_id == org_id,
            Membership.user_id == current_user.id
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized to access this organization's traces")

    # Count total
    count_query = select(func.count(AgentRun.id)).where(AgentRun.org_id == org_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get items
    query = (
        select(AgentRun)
        .where(AgentRun.org_id == org_id)
        .order_by(AgentRun.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items_result = await db.execute(query)
    items = items_result.scalars().all()

    return AgentRunListResponse(items=list(items), total=total)

@router.get("/{run_id}", response_model=AgentRunResponse)
async def get_trace(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve a specific trace and its steps.
    """
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run_id)
    )
    run = result.scalars().first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Trace not found")

    # Enforce tenant isolation
    from app.db.models import Membership
    member_result = await db.execute(
        select(Membership).where(
            Membership.org_id == run.org_id,
            Membership.user_id == current_user.id
        )
    )
    if not member_result.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized to access this trace")

    # Sort steps by latency_ms
    run.steps.sort(key=lambda s: s.latency_ms or 0)
    
    return run
