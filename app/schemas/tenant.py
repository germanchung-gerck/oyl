from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

TenantName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class TenantCreate(BaseModel):
    name: TenantName


class TenantUpdate(BaseModel):
    name: TenantName


class TenantResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
