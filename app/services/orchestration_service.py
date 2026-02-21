import re
import time
from typing import Any
from sqlalchemy.orm import Session

import ollama

from app.config import settings
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


def _extract_reasoning_steps(text: str) -> tuple[list[str], str]:
    """Parse <think>…</think> blocks from deepseek-r1 output."""
    steps: list[str] = []
    think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
    for match in think_pattern.finditer(text):
        raw = match.group(1).strip()
        steps.extend([s.strip() for s in raw.split("\n") if s.strip()])
    answer = think_pattern.sub("", text).strip()
    return steps, answer


def run_reasoning_inference(chunks: list[dict[str, Any]], query: str) -> dict[str, Any]:
    """
    Reasoning mode: use deepseek-r1:8b to process each chunk then synthesize.
    Returns answer, reasoning_steps, model_used, processing_time_seconds.
    """
    model = settings.REASONING_MODEL
    start = time.time()
    all_steps: list[str] = []
    chunk_answers: list[str] = []

    for chunk_info in chunks:
        prompt = (
            f"Context:\n{chunk_info['chunk']}\n\n"
            f"Question: {query}\n\n"
            "Think step by step and answer based only on the context above."
        )
        resp = ollama.generate(model=model, prompt=prompt)
        raw = resp.get("response", "")
        steps, answer = _extract_reasoning_steps(raw)
        all_steps.extend(steps)
        if answer:
            chunk_answers.append(answer)

    # Synthesize
    if len(chunk_answers) > 1:
        combined_context = "\n---\n".join(chunk_answers)
        synthesis_prompt = (
            f"You have gathered the following partial answers:\n{combined_context}\n\n"
            f"Original question: {query}\n\n"
            "Synthesize a final comprehensive answer with detailed reasoning."
        )
        synth_resp = ollama.generate(model=model, prompt=synthesis_prompt)
        synth_raw = synth_resp.get("response", "")
        synth_steps, final_answer = _extract_reasoning_steps(synth_raw)
        all_steps.extend(synth_steps)
    else:
        final_answer = chunk_answers[0] if chunk_answers else "No relevant information found."

    return {
        "answer": final_answer,
        "reasoning_steps": all_steps,
        "model_used": model,
        "processing_time_seconds": round(time.time() - start, 2),
    }


def run_fast_inference(chunks: list[dict[str, Any]], query: str) -> dict[str, Any]:
    """
    Fast mode: use qwen3:7b with all chunks as combined context.
    Returns answer, model_used, processing_time_seconds.
    """
    model = settings.FAST_MODEL
    start = time.time()

    combined_context = "\n\n---\n\n".join(c["chunk"] for c in chunks)
    prompt = (
        f"Context:\n{combined_context}\n\n"
        f"Question: {query}\n\n"
        "Answer concisely based on the context above."
    )
    resp = ollama.generate(model=model, prompt=prompt)
    answer = resp.get("response", "No relevant information found.")

    return {
        "answer": answer,
        "reasoning_steps": None,
        "model_used": model,
        "processing_time_seconds": round(time.time() - start, 2),
    }

