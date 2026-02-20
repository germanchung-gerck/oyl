from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from app.services.workspace_service import create_workspace, get_workspace
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(tags=["workspaces"])


@router.post("/tenants/{tenant_id}/workspaces", response_model=WorkspaceResponse, status_code=201)
def create_workspace_endpoint(
    tenant_id: str, data: WorkspaceCreate, db: Session = Depends(get_db)
) -> WorkspaceResponse:
    try:
        return create_workspace(db, tenant_id, data)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace_endpoint(workspace_id: str, db: Session = Depends(get_db)) -> WorkspaceResponse:
    try:
        return get_workspace(db, workspace_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc
