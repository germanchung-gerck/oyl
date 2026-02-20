from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.models.base import Base, TimestampMixin


class Teammate(Base, TimestampMixin):
    __tablename__ = "teammates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    orchestration_config: Mapped[dict] = mapped_column(JSON, nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="teammates")
    assistants: Mapped[list["Assistant"]] = relationship("Assistant", back_populates="teammate", cascade="all, delete-orphan")
