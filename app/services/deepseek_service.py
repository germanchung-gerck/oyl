"""DeepSeek integration via Ollama local inference."""
from typing import Any

from app.config import settings
from app.services.ollama_client import OllamaClient


class DeepSeekService:
    """Thin wrapper that routes DeepSeek model calls through Ollama."""

    def __init__(self, ollama: OllamaClient | None = None) -> None:
        self._ollama = ollama or OllamaClient()

    def extract_text(self, file_path: str) -> str:
        """Extract text from a document using the configured OCR model.

        For files whose content decodes cleanly as UTF-8, the text is returned
        directly.  For binary content (e.g. images, PDFs), the bytes are sent
        to the Ollama OCR model for extraction.
        """
        with open(file_path, "rb") as fh:
            content = fh.read()
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            prompt = (
                "Extract all readable text from the provided document. "
                "Return only the extracted text."
            )
            return self._ollama.generate(
                model=settings.OLLAMA_OCR_MODEL,
                prompt=prompt,
                images=[content],
            )

    def query(self, context: str, question: str) -> dict[str, Any]:
        """Send a RAG query to DeepSeek via Ollama."""
        prompt = (
            f"Answer the following question based on the context provided.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )
        answer = self._ollama.generate(
            model=settings.OLLAMA_REASONING_MODEL, prompt=prompt
        )
        return {"answer": answer, "model": settings.OLLAMA_REASONING_MODEL}
