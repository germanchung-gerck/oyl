from datetime import datetime
from pydantic import BaseModel


class InstructionCreate(BaseModel):
    system_prompt: str


class InstructionResponse(BaseModel):
    id: str
    assistant_id: str
    system_prompt: str
    updated_at: datetime

    model_config = {"from_attributes": True}
