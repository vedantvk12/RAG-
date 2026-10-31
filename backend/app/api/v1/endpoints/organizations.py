from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.db.models import User, Organization, Membership
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    MembershipCreate,
    MembershipResponse,
    MembershipUpdate
)
from app.api.deps import get_current_user, get_current_org_member, get_current_org_admin

router = APIRouter()

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_in: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new organization.
    The creator automatically becomes an admin of the new organization.
    """
    org = Organization(name=org_in.name)
    db.add(org)
    await db.flush()  # Flush to get the org.id
    
    membership = Membership(
        org_id=org.id,
        user_id=current_user.id,
        role="admin"
    )
    db.add(membership)
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get organization details. Requires membership.
    """
    # The get_current_org_member dependency already verifies membership.
    # We can just fetch the org.
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/{org_id}/members", response_model=List[MembershipResponse])
async def list_members(
    org_id: UUID,
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List members of an organization. Requires membership.
    """
    # Eager loading the user relationship isn't strict here since we just return IDs and roles mostly,
    # but the schema allows returning nested users. Let's do a simple query or join if needed.
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Membership)
        .where(Membership.org_id == org_id)
        .options(selectinload(Membership.user))
    )
    memberships = result.scalars().all()
    return memberships


@router.post("/{org_id}/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: UUID,
    member_in: MembershipCreate,
    admin_membership: Membership = Depends(get_current_org_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Add a user to the organization by email. Requires admin privileges.
    """
    # Find user by email
    user_result = await db.execute(select(User).where(User.email == member_in.email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already a member
    mem_result = await db.execute(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user.id)
    )
    if mem_result.scalars().first():
        raise HTTPException(status_code=400, detail="User is already a member")

    # Ensure role is valid
    if member_in.role not in ["admin", "member"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    new_membership = Membership(
        org_id=org_id,
        user_id=user.id,
        role=member_in.role
    )
    db.add(new_membership)
    await db.commit()
    await db.refresh(new_membership)
    
    # Reload with user data
    from sqlalchemy.orm import selectinload
    res = await db.execute(
        select(Membership)
        .where(Membership.org_id == org_id, Membership.user_id == user.id)
        .options(selectinload(Membership.user))
    )
    return res.scalars().first()


@router.patch("/{org_id}/members/{user_id}", response_model=MembershipResponse)
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    member_update: MembershipUpdate,
    admin_membership: Membership = Depends(get_current_org_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update a member's role. Requires admin privileges.
    """
    mem_result = await db.execute(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    )
    membership = mem_result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    if member_update.role not in ["admin", "member"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    membership.role = member_update.role
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    
    from sqlalchemy.orm import selectinload
    res = await db.execute(
        select(Membership)
        .where(Membership.org_id == org_id, Membership.user_id == user_id)
        .options(selectinload(Membership.user))
    )
    return res.scalars().first()


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    admin_membership: Membership = Depends(get_current_org_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Remove a member from the organization. Requires admin privileges.
    """
    # Prevent removing oneself to avoid orphaned organizations (unless handled specifically)
    if admin_membership.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself. Transfer ownership first.")

    mem_result = await db.execute(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    )
    membership = mem_result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    await db.delete(membership)
    await db.commit()
    return None
