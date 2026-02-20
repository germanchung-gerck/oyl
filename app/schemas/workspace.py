from datetime import datetime
from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
