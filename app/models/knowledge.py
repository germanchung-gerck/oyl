from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.models.base import Base, TimestampMixin


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assistant_id: Mapped[str] = mapped_column(String, ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vector_db_id: Mapped[str] = mapped_column(String(255), nullable=True)

    assistant: Mapped["Assistant"] = relationship("Assistant", back_populates="knowledge_bases")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(String, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=True)
    processed_status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)

    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
