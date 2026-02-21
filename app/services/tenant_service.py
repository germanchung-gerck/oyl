from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.utils.errors import NotFoundError


def create_tenant(db: Session, data: TenantCreate) -> Tenant:
    tenant = Tenant(name=data.name)
    db.add(tenant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Tenant with name '{data.name}' already exists")
    db.refresh(tenant)
    return tenant


def list_tenants(db: Session) -> list[Tenant]:
    return db.query(Tenant).order_by(Tenant.created_at.asc()).all()


def get_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise NotFoundError(f"Tenant {tenant_id} not found")
    return tenant


def update_tenant(db: Session, tenant_id: str, data: TenantUpdate) -> Tenant:
    tenant = get_tenant(db, tenant_id)
    tenant.name = data.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Tenant with name '{data.name}' already exists")
    db.refresh(tenant)
    return tenant


def delete_tenant(db: Session, tenant_id: str) -> None:
    tenant = get_tenant(db, tenant_id)
    db.delete(tenant)
    db.commit()
