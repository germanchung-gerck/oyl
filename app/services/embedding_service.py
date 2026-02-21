"""Embedding service: generate embeddings via Ollama and store/query in Chroma."""
from __future__ import annotations

import logging
from typing import Any

import chromadb
import ollama

from app.config import settings

logger = logging.getLogger(__name__)


def _chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)


def embed_text(text: str) -> list[float]:
    """Return embedding vector for *text* using the configured embedding model."""
    response = ollama.embeddings(model=settings.EMBEDDING_MODEL, prompt=text)
    return response["embedding"]


def get_or_create_collection(collection_name: str) -> chromadb.Collection:
    client = _chroma_client()
    return client.get_or_create_collection(name=collection_name)


def upsert_chunks(
    collection_name: str,
    chunk_ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    """Upsert text chunks with their embeddings and metadata into Chroma."""
    collection = get_or_create_collection(collection_name)
    collection.upsert(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def embed_and_store_chunks(
    collection_name: str,
    chunks: list[str],
    metadatas: list[dict[str, Any]],
    id_prefix: str = "",
) -> list[str]:
    """Embed each chunk and store in Chroma. Returns list of generated IDs."""
    import uuid

    ids: list[str] = []
    embeddings: list[list[float]] = []
    for chunk in chunks:
        ids.append(f"{id_prefix}{uuid.uuid4()}")
        embeddings.append(embed_text(chunk))

    upsert_chunks(collection_name, ids, embeddings, chunks, metadatas)
    return ids
