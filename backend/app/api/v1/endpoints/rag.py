from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, Membership
from app.services.rag.generator import rag_generator

router = APIRouter()

async def _get_user_org_id(user_id, db: AsyncSession):
    result = await db.execute(
        select(Membership).where(Membership.user_id == user_id)
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail="User does not belong to an organization")
    return membership.org_id

@router.post("/query", response_model=RAGQueryResponse)
async def generate_rag_response(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform Grounded RAG Generation.
    Strictly isolated to the user's organization.
    """
    org_id = await _get_user_org_id(current_user.id, db)
    
    try:
        if request.mode == "agentic":
            from app.services.rag.orchestrator import agentic_orchestrator
            response = await agentic_orchestrator.run(
                query=request.query,
                org_id=org_id,
                user_id=current_user.id,
                top_k=request.top_k,
                conversation_history=request.conversation_history
            )
        else:
            response = await rag_generator.generate_grounded_response(
                query=request.query,
                org_id=org_id,
                top_k=request.top_k,
                conversation_history=request.conversation_history
            )
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Prevent leaking raw LLM provider errors (like keys, urls, detailed messages)
        # We already mapped them in the generator/provider to generic exceptions.
        if "Security Error" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Security Error: Unauthorized data access detected.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred while generating the RAG response: {e}")
