from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PreApprovedItemCreate(BaseModel):
    item_name: str
    amount_limit: Optional[float] = None
    note: Optional[str] = None
    custom_variables: Optional[dict[str, str]] = None
    is_active: bool = True


class PreApprovedItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    item_name: str
    amount_limit: Optional[float]
    note: Optional[str]
    custom_variables: Optional[dict[str, str]] = None
    is_active: bool
    created_at: datetime


class PreApprovedItemUpdate(BaseModel):
    item_name: Optional[str] = None
    amount_limit: Optional[float] = None
    note: Optional[str] = None
    custom_variables: Optional[dict[str, str]] = None
    is_active: Optional[bool] = None
