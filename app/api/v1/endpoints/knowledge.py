import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.knowledge import KnowledgeBaseResponse, DocumentResponse
from app.schemas.instruction import InstructionCreate, InstructionResponse
from app.schemas.rag import BatchProcessRequest, BatchProcessResponse, ProcessingStatusResponse
from app.services.rag_service import (
    create_knowledge_base,
    add_document,
    upsert_instruction,
    process_document,
    get_knowledge_status,
)
from app.models.knowledge import KnowledgeBase, Document
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["knowledge"])

UPLOAD_DIR = "/tmp/oyl_uploads"


@router.post(
    "/assistants/{assistant_id}/knowledge/upload",
    response_model=DocumentResponse,
    status_code=201,
)
def upload_document(
    assistant_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    try:
        kb = create_knowledge_base(db, assistant_id, name=f"{assistant_id}-kb")
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename or "upload")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    raw_text = content.decode("utf-8", errors="replace")
    return add_document(db, kb.id, file_path=file_path, file_type=file.content_type, raw_content=raw_text)


@router.post(
    "/assistants/{assistant_id}/knowledge/process-batch",
    response_model=BatchProcessResponse,
)
def process_batch(
    assistant_id: str,
    body: BatchProcessRequest,
    db: Session = Depends(get_db),
) -> BatchProcessResponse:
    """Trigger OCR + embedding pipeline for pending documents.

    If ``document_ids`` is provided only those documents are processed;
    otherwise every *pending* document in the assistant's knowledge bases is processed.
    """
    try:
        status_info = get_knowledge_status(db, assistant_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc

    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.assistant_id == assistant_id).all()
    collection_name = f"assistant_{assistant_id}"

    target_docs: list[Document] = []
    for kb in kbs:
        for doc in kb.documents:
            if body.document_ids is not None:
                if doc.id in body.document_ids:
                    target_docs.append(doc)
            elif doc.processed_status == "pending":
                target_docs.append(doc)

    processed = 0
    failed = 0
    details: list[dict] = []

    for doc in target_docs:
        try:
            result = process_document(db, doc.id, collection_name)
            processed += 1
            details.append({"doc_id": doc.id, "status": "completed", **result})
        except Exception as exc:
            failed += 1
            details.append({"doc_id": doc.id, "status": "failed", "error": str(exc)})

    return BatchProcessResponse(processed=processed, failed=failed, details=details)


@router.get(
    "/assistants/{assistant_id}/knowledge/status",
    response_model=ProcessingStatusResponse,
)
def knowledge_status(
    assistant_id: str,
    db: Session = Depends(get_db),
) -> ProcessingStatusResponse:
    """Return document processing status for an assistant's knowledge base."""
    try:
        result = get_knowledge_status(db, assistant_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc
    return ProcessingStatusResponse(**result)


@router.post(
    "/assistants/{assistant_id}/instruction",
    response_model=InstructionResponse,
    status_code=201,
)
def set_instruction(
    assistant_id: str,
    data: InstructionCreate,
    db: Session = Depends(get_db),
) -> InstructionResponse:
    try:
        return upsert_instruction(db, assistant_id, data)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc
