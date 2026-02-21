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


SUPPORTED_STRATEGIES = {"weighted", "sequential", "parallel"}


def _assistant_order_for_teammate(teammate: Teammate) -> list[Assistant]:
    return sorted(teammate.assistants, key=lambda assistant: assistant.created_at)


def _resolve_assistants(teammate: Teammate, assistant_ids: list[str] | None) -> list[Assistant]:
    ordered = _assistant_order_for_teammate(teammate)
    by_id = {assistant.id: assistant for assistant in ordered}
    if not assistant_ids:
        return ordered
    return [by_id[assistant_id] for assistant_id in assistant_ids if assistant_id in by_id]


def _resolve_weights(config: dict[str, Any] | None, assistants: list[Assistant]) -> dict[str, float]:
    raw_weights = (config or {}).get("weights") or {}
    raw_name_weights = (config or {}).get("weights_by_name") or {}
    resolved: dict[str, float] = {}
    for assistant in assistants:
        weight = raw_weights.get(assistant.id, raw_name_weights.get(assistant.name, 1.0))
        try:
            numeric_weight = float(weight)
        except (TypeError, ValueError):
            numeric_weight = 1.0
        resolved[assistant.id] = numeric_weight if numeric_weight > 0 else 0.0
    return resolved


def _build_answer(assistant: Assistant, query: str) -> str:
    return f"{assistant.name} response to: {query}"


def _combine_answers(strategy: str, answers: list[str]) -> str:
    if not answers:
        return "No assistant responses available"
    if strategy == "weighted":
        return answers[0]
    return "\n".join(answers)


def _route_weighted(
    assistants: list[Assistant],
    weights: dict[str, float],
    max_assistants: int,
) -> list[Assistant]:
    ranked = sorted(
        assistants,
        key=lambda assistant: (weights.get(assistant.id, 0.0), assistant.created_at),
        reverse=True,
    )
    return ranked[:max_assistants]


def run_teammate_query(db: Session, teammate_id: str, query: str) -> dict[str, Any]:
    teammate = get_teammate(db, teammate_id)
    config = teammate.orchestration_config or {}
    strategy = str(config.get("strategy", "weighted")).lower()
    if strategy not in SUPPORTED_STRATEGIES:
        strategy = "weighted"

    configured_assistant_ids = config.get("assistant_ids")
    assistant_ids = configured_assistant_ids if isinstance(configured_assistant_ids, list) else None
    assistants = _resolve_assistants(teammate, assistant_ids)
    if not assistants:
        raise NotFoundError(f"No assistants configured for teammate {teammate_id}")

    weights = _resolve_weights(config, assistants)

    if strategy == "weighted":
        max_assistants = int(config.get("max_assistants", 1)) if str(config.get("max_assistants", "")).isdigit() else 1
        selected = _route_weighted(assistants, weights, max(1, max_assistants))
    else:
        selected = assistants

    responses: list[dict[str, Any]] = []
    for assistant in selected:
        responses.append(
            {
                "assistant_id": assistant.id,
                "assistant_name": assistant.name,
                "weight": weights.get(assistant.id, 1.0),
                "answer": _build_answer(assistant, query),
            }
        )

    return {
        "teammate_id": teammate.id,
        "strategy": strategy,
        "query": query,
        "selected_assistant_ids": [assistant.id for assistant in selected],
        "responses": responses,
        "result": _combine_answers(strategy, [response["answer"] for response in responses]),
    }
