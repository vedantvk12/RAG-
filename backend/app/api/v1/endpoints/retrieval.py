from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.db.models import User, Membership
from app.schemas.retrieval import SearchRequest, RerankSearchRequest, RetrievalResponse
from app.services.retrieval.retriever import HybridRetriever
from app.services.retrieval.reranker import reranker_service
from app.core.config import settings

router = APIRouter()

@router.post("/search", response_model=RetrievalResponse)
async def search_documents(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform hybrid retrieval (Dense + BM25 + RRF) for the authenticated user's organization.
    """
    # 1. Authorize and extract org_id
    org_id = await _get_user_org_id(current_user.id, db)
    
    # 2. Retrieve candidates
    results = await HybridRetriever.search(
        query=request.query,
        org_id=org_id,
        top_k=request.top_k
    )
    
    return RetrievalResponse(
        query=request.query,
        results=results
    )

@router.post("/rerank-search", response_model=RetrievalResponse)
async def rerank_search_documents(
    request: RerankSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform hybrid retrieval followed by cross-encoder reranking.
    """
    # 1. Authorize and extract org_id
    org_id = await _get_user_org_id(current_user.id, db)
    
    # 2. Retrieve candidates (fetch more candidates to allow reranker to work properly)
    candidates = await HybridRetriever.search(
        query=request.query,
        org_id=org_id,
        top_k=settings.FINAL_TOP_K  # Standard retrieval gets candidate pool
    )
    
    # 3. Rerank
    final_results = await reranker_service.rerank_results(
        query=request.query,
        candidates=candidates,
        org_id=org_id,
        top_k=request.top_k
    )
    
    return RetrievalResponse(
        query=request.query,
        results=final_results
    )

async def _get_user_org_id(user_id, db: AsyncSession):
    result = await db.execute(
        select(Membership).where(Membership.user_id == user_id)
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail="User does not belong to any organization")
    return membership.org_id
