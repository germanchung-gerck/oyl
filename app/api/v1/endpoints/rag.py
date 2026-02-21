"""RAG document management endpoints: upload with OCR, batch process, status."""
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.rag import DocumentUploadResponse, BatchProcessRequest, BatchProcessResponse, KnowledgeStatusResponse
from app.services.rag_service import (
    create_knowledge_base,
    add_document,
    process_document,
    get_knowledge_status,
)
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["rag"])

UPLOAD_DIR = "/tmp/oyl_uploads"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".txt", ".md", ".csv"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post(
    "/assistants/{assistant_id}/knowledge/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
)
def upload_document_with_ocr(
    assistant_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a document and trigger OCR processing pipeline."""
    # Validate file extension
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 50MB limit",
        )

    try:
        kb = create_knowledge_base(db, assistant_id, name=f"{assistant_id}-kb")
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    raw_text = None
    if ext in {".txt", ".md", ".csv"}:
        raw_text = content.decode("utf-8", errors="replace")

    doc = add_document(db, kb.id, file_path=file_path, file_type=file.content_type, raw_content=raw_text)

    collection_name = f"assistant_{assistant_id}"
    try:
        stats = process_document(db, doc.id, collection_name=collection_name)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {exc}",
        ) from exc

    return DocumentUploadResponse(
        document_id=doc.id,
        knowledge_base_id=kb.id,
        file_name=filename,
        file_type=file.content_type,
        chunks_created=stats["chunks_created"],
        tags_generated=stats["tags_generated"],
        processing_time_seconds=stats["processing_time_seconds"],
        status="processed",
    )


@router.post(
    "/assistants/{assistant_id}/knowledge/process-batch",
    response_model=BatchProcessResponse,
    status_code=200,
)
def process_batch(
    assistant_id: str,
    body: BatchProcessRequest,
    db: Session = Depends(get_db),
) -> BatchProcessResponse:
    """Trigger OCR processing for a batch of already-uploaded documents."""
    from app.services.orchestration_service import get_assistant

    try:
        get_assistant(db, assistant_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc

    collection_name = f"assistant_{assistant_id}"
    results: list[DocumentUploadResponse] = []
    processed = 0
    failed = 0

    for doc_id in body.document_ids:
        try:
            stats = process_document(db, doc_id, collection_name=collection_name)
            from app.models.knowledge import Document

            doc = db.get(Document, doc_id)
            results.append(
                DocumentUploadResponse(
                    document_id=doc_id,
                    knowledge_base_id=doc.knowledge_base_id if doc else "",
                    file_name=doc.file_path.split("/")[-1] if doc else doc_id,
                    file_type=doc.file_type if doc else None,
                    chunks_created=stats["chunks_created"],
                    tags_generated=stats["tags_generated"],
                    processing_time_seconds=stats["processing_time_seconds"],
                    status="processed",
                )
            )
            processed += 1
        except Exception as exc:
            failed += 1
            results.append(
                DocumentUploadResponse(
                    document_id=doc_id,
                    knowledge_base_id="",
                    file_name=doc_id,
                    file_type=None,
                    chunks_created=0,
                    tags_generated=0,
                    processing_time_seconds=0.0,
                    status=f"failed: {exc}",
                )
            )

    return BatchProcessResponse(processed=processed, failed=failed, results=results)


@router.get(
    "/assistants/{assistant_id}/knowledge/status",
    response_model=KnowledgeStatusResponse,
)
def knowledge_status(
    assistant_id: str,
    db: Session = Depends(get_db),
) -> KnowledgeStatusResponse:
    """Return document processing status and metrics for an assistant."""
    try:
        data = get_knowledge_status(db, assistant_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc
    return KnowledgeStatusResponse(**data)
