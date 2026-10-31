from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.decision import DecisionRequest
from app.services.decisions.engine import decision_engine
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze")
async def analyze_decision(
    request: DecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    from app.db.models import Membership
    result = await db.execute(select(Membership).where(Membership.user_id == current_user.id))
    memberships = result.scalars().all()
    if not memberships:
        raise HTTPException(status_code=403, detail="User does not belong to any organization")
    
    org_id = memberships[0].org_id
    user_id = current_user.id
    
    try:
        response = await decision_engine.analyze(
            query=request.query,
            org_id=org_id,
            user_id=user_id
        )
        return response
    except TimeoutError as e:
        logger.warning(f"Decision timeout: {e}")
        from app.schemas.decision import AbstainDecisionResponse, DecisionTrace
        return AbstainDecisionResponse(
            reason=str(e),
            decision_trace=DecisionTrace(
                run_id="00000000-0000-0000-0000-000000000000",
                iterations=0,
                llm_calls=0,
                retrieval_queries=0,
                latency_ms=0.0,
                evidence_count=0,
                document_count=0
            )
        )
    except Exception as e:
        logger.error(f"Decision engine error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
