from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.rag import QueryRequest, QueryResponse
from app.services.orchestration_service import get_teammate
from app.services.rag_pipeline import RAGPipeline
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["orchestration"])


@router.post("/teammates/{teammate_id}/query", response_model=QueryResponse)
def query_teammate(
    teammate_id: str,
    body: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """Query a teammate using dual-mode RAG inference.

    Set ``mode`` to ``"reasoning"`` for step-by-step DeepSeek-R1 answers or
    ``"fast"`` (default) for quick Qwen answers.
    """
    try:
        teammate = get_teammate(db, teammate_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc

    mode = body.mode if body.mode in ("reasoning", "fast") else "fast"
    collection_name = f"teammate_{teammate_id}"

    pipeline = RAGPipeline()
    result = pipeline.query(
        query_text=body.query,
        collection_name=collection_name,
        mode=mode,
    )

    return QueryResponse(
        teammate_id=teammate.id,
        query=body.query,
        answer=result["answer"],
        mode=result["mode"],
        model=result["model"],
        sources=result["sources"],
        query_tags=result["query_tags"],
        processing_time_ms=result["processing_time_ms"],
    )
