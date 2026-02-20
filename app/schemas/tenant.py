from datetime import datetime
from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
