"""DeepSeek-OCR integration placeholder."""
from typing import Any


class DeepSeekService:
    """Thin wrapper for DeepSeek-OCR API calls."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def extract_text(self, file_path: str) -> str:
        """Extract text from a document using DeepSeek-OCR."""
        # TODO: integrate with DeepSeek-OCR SDK
        raise NotImplementedError("DeepSeek-OCR integration not yet implemented")

    def query(self, context: str, question: str) -> dict[str, Any]:
        """Send a RAG query to DeepSeek."""
        # TODO: integrate with DeepSeek API
        raise NotImplementedError("DeepSeek query not yet implemented")
