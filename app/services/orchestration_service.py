from typing import Any
from sqlalchemy.orm import Session

from app.models.teammate import Teammate
from app.models.assistant import Assistant
from app.schemas.teammate import TeammateCreate
from app.schemas.assistant import AssistantCreate
from app.services.workspace_service import get_workspace
from app.utils.errors import NotFoundError


def get_teammate(db: Session, teammate_id: str) -> Teammate:
    teammate = db.get(Teammate, teammate_id)
    if not teammate:
        raise NotFoundError(f"Teammate {teammate_id} not found")
    return teammate


def create_teammate(db: Session, workspace_id: str, data: TeammateCreate) -> Teammate:
    get_workspace(db, workspace_id)
    teammate = Teammate(
        workspace_id=workspace_id,
        name=data.name,
        orchestration_config=data.orchestration_config,
    )
    db.add(teammate)
    db.commit()
    db.refresh(teammate)
    return teammate


def get_assistant(db: Session, assistant_id: str) -> Assistant:
    assistant = db.get(Assistant, assistant_id)
    if not assistant:
        raise NotFoundError(f"Assistant {assistant_id} not found")
    return assistant


def create_assistant(db: Session, teammate_id: str, data: AssistantCreate) -> Assistant:
    get_teammate(db, teammate_id)
    assistant = Assistant(teammate_id=teammate_id, name=data.name)
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return assistant
