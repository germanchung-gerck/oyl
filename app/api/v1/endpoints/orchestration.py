from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.orchestration_service import get_teammate
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["orchestration"])


@router.post("/teammates/{teammate_id}/query")
def query_teammate(
    teammate_id: str,
    body: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        teammate = get_teammate(db, teammate_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc

    # Placeholder: return teammate config and submitted query
    return {
        "teammate_id": teammate.id,
        "query": body.get("query", ""),
        "result": "Orchestration not yet implemented",
    }
