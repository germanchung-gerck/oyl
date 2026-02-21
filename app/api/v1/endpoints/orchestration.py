import time
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.query import QueryRequest, QueryResponse, ChunkSource
from app.services.orchestration_service import get_teammate, run_reasoning_inference, run_fast_inference
from app.services.tagging_service import generate_query_tags
from app.services.retrieval_service import retrieve_chunks
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["orchestration"])


@router.post("/teammates/{teammate_id}/query", response_model=QueryResponse)
def query_teammate(
    teammate_id: str,
    body: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """Query a teammate with dual-mode inference (reasoning or fast)."""
    try:
        teammate = get_teammate(db, teammate_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc

    # Determine the assistant and collection for retrieval
    from app.models.assistant import Assistant
    from app.models.knowledge import KnowledgeBase

    assistant = db.query(Assistant).filter(Assistant.teammate_id == teammate_id).first()
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No assistant found for teammate {teammate_id}",
        )

    collection_name = f"assistant_{assistant.id}"

    # Generate query tags for semantic filtering
    try:
        query_tags = generate_query_tags(body.query)
    except Exception:
        query_tags = []

    # Retrieve relevant chunks
    try:
        chunks = retrieve_chunks(
            collection_name=collection_name,
            query=body.query,
            top_k=body.top_k,
            tag_filter=query_tags if query_tags else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Retrieval failed: {exc}",
        ) from exc

    if not chunks:
        # Return empty result rather than an error
        from app.config import settings
        model = settings.REASONING_MODEL if body.inference_mode == "reasoning" else settings.FAST_MODEL
        return QueryResponse(
            query=body.query,
            inference_mode=body.inference_mode,
            answer="No relevant information found in the knowledge base.",
            reasoning_steps=None,
            sources=[],
            model_used=model,
            processing_time_seconds=0.0,
            inference_mode_used=body.inference_mode,
        )

    # Run inference based on mode
    try:
        if body.inference_mode == "reasoning":
            inference_result = run_reasoning_inference(chunks, body.query)
        else:
            inference_result = run_fast_inference(chunks, body.query)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Inference failed: {exc}",
        ) from exc

    sources = [
        ChunkSource(
            chunk=c["chunk"],
            source_document=c["source_document"],
            relevance_score=c["relevance_score"],
            tags=c["tags"],
        )
        for c in chunks
    ]

    return QueryResponse(
        query=body.query,
        inference_mode=body.inference_mode,
        answer=inference_result["answer"],
        reasoning_steps=inference_result.get("reasoning_steps"),
        sources=sources,
        model_used=inference_result["model_used"],
        processing_time_seconds=inference_result["processing_time_seconds"],
        inference_mode_used=body.inference_mode,
    )

