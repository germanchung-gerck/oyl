from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.assistant import AssistantCreate, AssistantResponse
from app.services.orchestration_service import create_assistant, get_assistant
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["assistants"])


@router.post("/teammates/{teammate_id}/assistants", response_model=AssistantResponse, status_code=201)
def create_assistant_endpoint(
    teammate_id: str, data: AssistantCreate, db: Session = Depends(get_db)
) -> AssistantResponse:
    try:
        return create_assistant(db, teammate_id, data)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc


@router.get("/assistants/{assistant_id}", response_model=AssistantResponse)
def get_assistant_endpoint(assistant_id: str, db: Session = Depends(get_db)) -> AssistantResponse:
    try:
        return get_assistant(db, assistant_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc
