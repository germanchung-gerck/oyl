from datetime import datetime
from pydantic import BaseModel


class KnowledgeBaseResponse(BaseModel):
    id: str
    assistant_id: str
    name: str
    vector_db_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: str
    knowledge_base_id: str
    file_path: str
    file_type: str | None
    processed_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
