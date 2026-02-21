from datetime import datetime
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    knowledge_base_id: str
    file_name: str
    file_type: str | None
    chunks_created: int
    tags_generated: int
    processing_time_seconds: float
    status: str


class BatchProcessRequest(BaseModel):
    document_ids: list[str]


class BatchProcessResponse(BaseModel):
    processed: int
    failed: int
    results: list[DocumentUploadResponse]


class KnowledgeStatusResponse(BaseModel):
    assistant_id: str
    knowledge_base_id: str | None
    total_documents: int
    processed_documents: int
    pending_documents: int
    total_chunks: int
    embedding_model: str
    vector_store_collection: str | None
