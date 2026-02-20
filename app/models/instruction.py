from datetime import datetime
from sqlalchemy import String, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.models.base import Base


class Instruction(Base):
    __tablename__ = "instructions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assistant_id: Mapped[str] = mapped_column(String, ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False, unique=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    assistant: Mapped["Assistant"] = relationship("Assistant", back_populates="instruction")
