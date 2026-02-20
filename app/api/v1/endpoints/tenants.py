from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant_service import create_tenant, get_tenant
from app.utils.errors import NotFoundError, not_found_exception

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse, status_code=201)
def create_tenant_endpoint(data: TenantCreate, db: Session = Depends(get_db)) -> TenantResponse:
    return create_tenant(db, data)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant_endpoint(tenant_id: str, db: Session = Depends(get_db)) -> TenantResponse:
    try:
        return get_tenant(db, tenant_id)
    except NotFoundError as exc:
        raise not_found_exception(str(exc)) from exc
