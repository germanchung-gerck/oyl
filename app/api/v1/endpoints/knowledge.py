import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.instruction import InstructionCreate, InstructionResponse
from app.services.rag_service import upsert_instruction
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["knowledge"])


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
