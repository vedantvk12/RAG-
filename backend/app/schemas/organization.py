from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.schemas.user import UserResponse

class OrganizationBase(BaseModel):
    name: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class MembershipBase(BaseModel):
    role: str

class MembershipCreate(BaseModel):
    email: str
    role: str = "member"

class MembershipUpdate(BaseModel):
    role: str

class MembershipResponse(BaseModel):
    org_id: UUID
    user_id: UUID
    role: str
    user: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True
