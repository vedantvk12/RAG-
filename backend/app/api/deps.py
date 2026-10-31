from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Path, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User, Membership
from app.schemas.auth import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def get_token(request: Request, token: str = Depends(oauth2_scheme)) -> str:
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Remove Bearer prefix if present in cookie (though we won't set it with prefix)
    if token.startswith("Bearer "):
        token = token[7:]
    return token

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_token)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception

    try:
        user_uuid = UUID(token_data.sub)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalars().first()
    if not user:
        raise credentials_exception
    return user


async def get_current_org_member(
    org_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Membership:
    """
    Enforces tenant isolation by verifying the current_user is a member of org_id.
    Returns the Membership object so routes can verify roles.
    """
    result = await db.execute(
        select(Membership)
        .where(Membership.org_id == org_id, Membership.user_id == current_user.id)
    )
    membership = result.scalars().first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions or organization not found"
        )
    return membership


async def get_current_org_admin(
    membership: Membership = Depends(get_current_org_member)
) -> Membership:
    """
    Ensures the current user is an admin of the specified organization.
    """
    if membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return membership
