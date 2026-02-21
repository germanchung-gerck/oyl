"""Thin HTTP client for the Ollama local inference API."""
from __future__ import annotations

import base64
from typing import Any

import httpx

from app.config import settings


class OllamaClient:
    """Wraps Ollama's /api/generate and /api/embeddings endpoints."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.OLLAMA_TIMEOUT

    def generate(
        self,
        model: str,
        prompt: str,
        images: list[bytes] | None = None,
    ) -> str:
        """Run text generation (optionally multimodal) and return the response string."""
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if images:
            payload["images"] = [base64.b64encode(img).decode() for img in images]
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama generate failed for model '{model}': "
                f"HTTP {exc.response.status_code}"
            ) from exc
        return response.json()["response"]

    def embed(self, model: str, text: str) -> list[float]:
        """Return an embedding vector for *text* using *model*."""
        try:
            response = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama embed failed for model '{model}': "
                f"HTTP {exc.response.status_code}"
            ) from exc
        return response.json()["embedding"]
