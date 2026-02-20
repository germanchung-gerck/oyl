from datetime import datetime
from pydantic import BaseModel


class AssistantCreate(BaseModel):
    name: str


class AssistantResponse(BaseModel):
    id: str
    teammate_id: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
