from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate
from app.services.tenant_service import get_tenant
from app.utils.errors import NotFoundError


def create_workspace(db: Session, tenant_id: str, data: WorkspaceCreate) -> Workspace:
    get_tenant(db, tenant_id)  # Validate tenant exists
    workspace = Workspace(tenant_id=tenant_id, name=data.name)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def get_workspace(db: Session, workspace_id: str) -> Workspace:
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise NotFoundError(f"Workspace {workspace_id} not found")
    return workspace
