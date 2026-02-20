import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.knowledge import KnowledgeBaseResponse, DocumentResponse
from app.schemas.instruction import InstructionCreate, InstructionResponse
from app.services.rag_service import create_knowledge_base, add_document, upsert_instruction
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
