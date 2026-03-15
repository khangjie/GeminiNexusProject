from datetime import datetime
from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str


class CompanyRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    owner_id: str
    created_at: datetime
