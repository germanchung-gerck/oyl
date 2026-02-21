from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.teammate import TeammateQueryRequest, TeammateQueryResponse
from app.services.orchestration_service import run_teammate_query
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["orchestration"])


@router.post("/teammates/{teammate_id}/query", response_model=TeammateQueryResponse)
def query_teammate(
    teammate_id: str,
    body: TeammateQueryRequest,
    db: Session = Depends(get_db),
) -> TeammateQueryResponse:
    try:
        return run_teammate_query(db, teammate_id, body.query)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc
