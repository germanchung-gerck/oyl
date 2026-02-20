from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.teammate import TeammateCreate, TeammateResponse
from app.services.orchestration_service import create_teammate, get_teammate
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["teammates"])


@router.post("/workspaces/{workspace_id}/teammates", response_model=TeammateResponse, status_code=201)
def create_teammate_endpoint(
    workspace_id: str, data: TeammateCreate, db: Session = Depends(get_db)
) -> TeammateResponse:
    try:
        return create_teammate(db, workspace_id, data)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc


@router.get("/teammates/{teammate_id}", response_model=TeammateResponse)
def get_teammate_endpoint(teammate_id: str, db: Session = Depends(get_db)) -> TeammateResponse:
    try:
        return get_teammate(db, teammate_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc
