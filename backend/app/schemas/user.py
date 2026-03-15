from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    role: Literal["owner", "worker"]
    google_uid: Optional[str] = None
    company_id: Optional[str] = None


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    email: str
    name: str
    role: str
    company_id: Optional[str]
    created_at: datetime


class UserUpdate(BaseModel):
    name: Optional[str] = None
    company_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
