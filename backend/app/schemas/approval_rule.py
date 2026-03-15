from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ApprovalRuleCreate(BaseModel):
    name: str
    prompt: str
    applies_to_preapproved: bool = True
    is_active: bool = True


class ApprovalRuleRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    name: str
    prompt: str
    applies_to_preapproved: bool = True
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ApprovalRuleUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    applies_to_preapproved: Optional[bool] = None
    is_active: Optional[bool] = None
