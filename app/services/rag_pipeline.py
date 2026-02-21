"""Core RAG pipeline: OCR → chunking → embedding → tagging → Chroma retrieval → inference."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

import chromadb

from app.config import settings
from app.services.ollama_client import OllamaClient


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split *text* into overlapping character-level chunks."""
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += chunk_size - chunk_overlap
    return chunks


# ---------------------------------------------------------------------------
# RAG pipeline
# ---------------------------------------------------------------------------

class RAGPipeline:
    """Orchestrates document ingestion and query inference."""

    def __init__(
        self,
        ollama: OllamaClient | None = None,
        chroma_host: str | None = None,
        chroma_port: int | None = None,
    ) -> None:
        self.ollama = ollama or OllamaClient()
        self._chroma_host = chroma_host or settings.CHROMA_HOST
        self._chroma_port = chroma_port or settings.CHROMA_PORT
        self._chroma_client: chromadb.HttpClient | None = None

    # ------------------------------------------------------------------
    # Chroma helpers
    # ------------------------------------------------------------------

    def _get_chroma(self) -> chromadb.HttpClient:
        if self._chroma_client is None:
            self._chroma_client = chromadb.HttpClient(
                host=self._chroma_host, port=self._chroma_port
            )
        return self._chroma_client

    def _get_collection(self, collection_name: str) -> Any:
        return self._get_chroma().get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Text extraction (OCR)
    # ------------------------------------------------------------------

    def extract_text(self, content: bytes, file_type: str | None) -> str:
        """Extract plain text from *content*.

        For plain text types the bytes are decoded directly.  For binary
        formats (PDF, images) the bytes are forwarded to the configured Ollama
        OCR model as a multimodal request so that the model handles extraction.
        """
        mime = (file_type or "").lower()
        if mime.startswith("text/") or mime in {"application/json", "text/csv"}:
            return content.decode("utf-8", errors="replace")

        if mime == "application/pdf" or mime.startswith("image/"):
            prompt = (
                "Extract all readable text from the provided document or image. "
                "Return only the extracted text without commentary."
            )
            return self.ollama.generate(
                model=settings.OLLAMA_OCR_MODEL,
                prompt=prompt,
                images=[content],
            )

        # Fallback: best-effort UTF-8 decode
        try:
            return content.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")

    # ------------------------------------------------------------------
    # Tagging
    # ------------------------------------------------------------------

    def tag_text(self, text: str) -> list[str]:
        """Return a list of descriptive tags for *text* using the tagging model."""
        snippet = text[:2000]
        prompt = (
            "Generate up to 5 short, lowercase keyword tags that best describe the "
            f"following text. Return only the tags as a comma-separated list.\n\n{snippet}"
        )
        raw = self.ollama.generate(model=settings.OLLAMA_TAGGING_MODEL, prompt=prompt)
        tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
        return tags[:5]

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        return self.ollama.embed(model=settings.OLLAMA_EMBEDDING_MODEL, text=text)

    # ------------------------------------------------------------------
    # Document indexing
    # ------------------------------------------------------------------

    def index_document(
        self,
        doc_id: str,
        content: bytes,
        file_type: str | None,
        collection_name: str,
        source_name: str = "",
    ) -> dict[str, Any]:
        """Full pipeline: OCR → chunk → embed → tag → store in Chroma.

        Returns a summary dict with chunk count and tags.
        """
        text = self.extract_text(content, file_type)
        chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)

        collection = self._get_collection(collection_name)

        doc_tags: list[str] = self.tag_text(text)
        tags_str = ",".join(doc_tags)

        ids: list[str] = []
        embeddings: list[list[float]] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for idx, chunk in enumerate(chunks):
            chunk_embedding = self.embed(chunk)
            chunk_id = f"{doc_id}_chunk_{idx}"
            ids.append(chunk_id)
            embeddings.append(chunk_embedding)
            documents.append(chunk)
            metadatas.append(
                {
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "source": source_name,
                    "file_type": file_type or "",
                    "tags": tags_str,
                }
            )

        if ids:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

        return {"chunk_count": len(chunks), "tags": doc_tags}

    # ------------------------------------------------------------------
    # Query pipeline
    # ------------------------------------------------------------------

    def _retrieve(
        self,
        query_text: str,
        collection_name: str,
        query_tags: list[str],
        n_results: int,
    ) -> list[dict[str, Any]]:
        """Embed query and retrieve top-*n_results* chunks from Chroma."""
        collection = self._get_collection(collection_name)
        query_embedding = self.embed(query_text)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[dict[str, Any]] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            chunk_tags = [t for t in meta.get("tags", "").split(",") if t]
            # Apply tag-based relevance boost: prefer chunks that share tags with query.
            # Falls back to all retrieved chunks when no overlap is found so that the
            # pipeline always returns a response even for broad or untagged queries.
            if query_tags and not any(qt in chunk_tags for qt in query_tags):
                continue  # skip chunks with no tag overlap when query has tags
            chunks.append({"text": doc, "metadata": meta, "distance": dist})

        # If tag filtering removed everything, fall back to all retrieved chunks
        if not chunks:
            for doc, meta, dist in zip(docs, metas, dists):
                chunks.append({"text": doc, "metadata": meta, "distance": dist})

        return chunks

    def _infer_reasoning(self, query: str, chunks: list[dict[str, Any]]) -> str:
        """Deep reasoning inference: process each chunk then synthesize."""
        partial_answers: list[str] = []
        for chunk in chunks:
            prompt = (
                "Think step-by-step. Using only the context below, answer the question.\n\n"
                f"Context:\n{chunk['text']}\n\nQuestion: {query}\n\nAnswer:"
            )
            answer = self.ollama.generate(
                model=settings.OLLAMA_REASONING_MODEL, prompt=prompt
            )
            partial_answers.append(answer)

        if len(partial_answers) == 1:
            return partial_answers[0]

        combined_context = "\n\n---\n\n".join(partial_answers)
        synthesis_prompt = (
            "You have received several partial answers from different sources. "
            "Synthesize them into a single coherent, step-by-step answer.\n\n"
            f"Partial answers:\n{combined_context}\n\nOriginal question: {query}\n\n"
            "Synthesized answer:"
        )
        return self.ollama.generate(
            model=settings.OLLAMA_REASONING_MODEL, prompt=synthesis_prompt
        )

    def _infer_fast(self, query: str, chunks: list[dict[str, Any]]) -> str:
        """Fast inference: combine all chunks into one prompt."""
        context = "\n\n".join(c["text"] for c in chunks)
        prompt = (
            f"Answer concisely based on the following context.\n\n"
            f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        )
        return self.ollama.generate(model=settings.OLLAMA_FAST_MODEL, prompt=prompt)

    def query(
        self,
        query_text: str,
        collection_name: str,
        mode: str = "fast",
    ) -> dict[str, Any]:
        """Full query pipeline: tag → embed → retrieve → infer.

        Parameters
        ----------
        query_text:
            The user's question.
        collection_name:
            Chroma collection to search (typically the assistant's KB id).
        mode:
            ``"reasoning"`` (deepseek-r1) or ``"fast"`` (qwen).

        Returns
        -------
        dict with keys: answer, mode, model, sources, processing_time_ms
        """
        start = time.time()

        query_tags = self.tag_text(query_text)
        chunks = self._retrieve(
            query_text, collection_name, query_tags, settings.MAX_RETRIEVED_CHUNKS
        )

        if not chunks:
            return {
                "answer": "No relevant documents found in the knowledge base.",
                "mode": mode,
                "model": settings.OLLAMA_FAST_MODEL if mode == "fast" else settings.OLLAMA_REASONING_MODEL,
                "sources": [],
                "query_tags": query_tags,
                "processing_time_ms": int((time.time() - start) * 1000),
            }

        if mode == "reasoning":
            answer = self._infer_reasoning(query_text, chunks)
            model_used = settings.OLLAMA_REASONING_MODEL
        else:
            answer = self._infer_fast(query_text, chunks)
            model_used = settings.OLLAMA_FAST_MODEL

        sources = list(
            {c["metadata"].get("source", "") for c in chunks if c["metadata"].get("source")}
        )

        return {
            "answer": answer,
            "mode": mode,
            "model": model_used,
            "sources": sources,
            "query_tags": query_tags,
            "processing_time_ms": int((time.time() - start) * 1000),
        }
