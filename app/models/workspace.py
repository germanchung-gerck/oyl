from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.models.base import Base, TimestampMixin


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="workspaces")
    teammates: Mapped[list["Teammate"]] = relationship("Teammate", back_populates="workspace", cascade="all, delete-orphan")
