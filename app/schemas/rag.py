from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    mode: str = "fast"  # "fast" | "reasoning"


class QueryResponse(BaseModel):
    teammate_id: str
    query: str
    answer: str
    mode: str
    model: str
    sources: list[str]
    query_tags: list[str]
    processing_time_ms: int


class BatchProcessRequest(BaseModel):
    document_ids: list[str] | None = None  # None → process all pending docs


class BatchProcessResponse(BaseModel):
    processed: int
    failed: int
    details: list[dict[str, Any]]


class ProcessingStatusResponse(BaseModel):
    assistant_id: str
    total: int
    pending: int
    completed: int
    failed: int
    documents: list[dict[str, Any]]
