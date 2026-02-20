from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate
from app.utils.errors import NotFoundError


def create_tenant(db: Session, data: TenantCreate) -> Tenant:
    tenant = Tenant(name=data.name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def get_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise NotFoundError(f"Tenant {tenant_id} not found")
    return tenant
