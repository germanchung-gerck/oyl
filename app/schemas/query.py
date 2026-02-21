from typing import Literal
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str
    inference_mode: Literal["reasoning", "fast"] = "fast"
    top_k: int = Field(default=5, ge=1, le=20)


class ChunkSource(BaseModel):
    chunk: str
    source_document: str
    relevance_score: float
    tags: list[str]


class QueryResponse(BaseModel):
    query: str
    inference_mode: str
    answer: str
    reasoning_steps: list[str] | None = None
    sources: list[ChunkSource]
    model_used: str
    processing_time_seconds: float
    inference_mode_used: str
