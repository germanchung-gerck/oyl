from datetime import datetime
from typing import Any
from pydantic import BaseModel


class TeammateCreate(BaseModel):
    name: str
    orchestration_config: dict[str, Any] | None = None


class TeammateResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    orchestration_config: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
