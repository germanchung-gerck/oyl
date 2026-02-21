"""Tagging service: generate semantic tags for text chunks via Ollama."""
from __future__ import annotations

import logging
import re

import ollama

from app.config import settings
logger = logging.getLogger(__name__)

_TAG_PROMPT_TEMPLATE = (
    "Generate {n} short semantic tags (single words or short phrases) for the following text. "
    "Return only a comma-separated list of tags, nothing else.\n\nText:\n{text}\n\nTags:"
)


def _parse_tags(raw: str) -> list[str]:
    tags = [t.strip().lower() for t in re.split(r"[,\n]", raw) if t.strip()]
    return tags


def generate_tags(text: str, n: int | None = None) -> list[str]:
    """Generate *n* semantic tags for *text* using the tagging model."""
    if n is None:
        n = settings.TAGS_PER_CHUNK
    prompt = _TAG_PROMPT_TEMPLATE.format(n=n, text=text[:2000])
    try:
        response = ollama.generate(model=settings.TAGGING_MODEL, prompt=prompt)
        raw = response.get("response", "")
        tags = _parse_tags(raw)
        return tags[:n]
    except Exception as exc:  # pragma: no cover
        logger.warning("Tagging failed: %s", exc)
        return []


def generate_query_tags(query: str) -> list[str]:
    """Generate semantic tags for a query to aid retrieval filtering."""
    return generate_tags(query, n=settings.TAGS_PER_CHUNK)
