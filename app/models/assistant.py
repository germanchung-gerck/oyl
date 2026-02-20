from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.models.base import Base, TimestampMixin


class Assistant(Base, TimestampMixin):
    __tablename__ = "assistants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    teammate_id: Mapped[str] = mapped_column(String, ForeignKey("teammates.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    teammate: Mapped["Teammate"] = relationship("Teammate", back_populates="assistants")
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship("KnowledgeBase", back_populates="assistant", cascade="all, delete-orphan")
    instruction: Mapped["Instruction"] = relationship("Instruction", back_populates="assistant", uselist=False, cascade="all, delete-orphan")
