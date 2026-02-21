"""DeepSeek-OCR integration via Ollama."""
from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import ollama

from app.config import settings

logger = logging.getLogger(__name__)


class DeepSeekService:
    """Wrapper for DeepSeek-OCR via Ollama (local inference)."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.OCR_MODEL

    def extract_text(self, file_path: str) -> str:
        """Extract text from a document using DeepSeek-OCR via Ollama.

        Supports plain text files directly, and image files via multimodal prompt.
        PDF files are converted to images per page before OCR.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in {".txt", ".md", ".csv"}:
            return path.read_text(encoding="utf-8", errors="replace")

        if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}:
            return self._ocr_image(file_path)

        if suffix == ".pdf":
            return self._ocr_pdf(file_path)

        # Fallback: attempt to read as text
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Could not read %s as text: %s", file_path, exc)
            return ""

    def _ocr_image(self, image_path: str) -> str:
        """Run OCR on a single image file."""
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        response = ollama.generate(
            model=self.model,
            prompt="Extract all text from this image. Return only the extracted text.",
            images=[image_data],
        )
        return response.get("response", "")

    def _ocr_pdf(self, pdf_path: str) -> str:
        """Convert PDF pages to images and OCR each page."""
        try:
            from pdf2image import convert_from_path
        except ImportError:  # pragma: no cover
            logger.error("pdf2image not installed; cannot process PDF")
            return ""

        import tempfile
        import os

        texts: list[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            images = convert_from_path(pdf_path, output_folder=tmpdir, fmt="png")
            for i, img in enumerate(images):
                img_path = os.path.join(tmpdir, f"page_{i}.png")
                img.save(img_path, "PNG")
                page_text = self._ocr_image(img_path)
                texts.append(page_text)

        return "\n\n".join(texts)

    def query(self, context: str, question: str) -> dict[str, Any]:
        """Send a RAG query (kept for backward compatibility)."""
        prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        response = ollama.generate(model=settings.FAST_MODEL, prompt=prompt)
        return {"answer": response.get("response", ""), "model": settings.FAST_MODEL}

