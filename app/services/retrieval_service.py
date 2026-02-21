"""Retrieval service: semantic search with optional tag-based filtering."""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.services.embedding_service import embed_text, get_or_create_collection

logger = logging.getLogger(__name__)


def retrieve_chunks(
    collection_name: str,
    query: str,
    top_k: int | None = None,
    tag_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Semantic search over *collection_name*.

    Returns a list of dicts with keys: chunk, source_document, relevance_score, tags.
    """
    if top_k is None:
        top_k = settings.TOP_K_CHUNKS

    collection = get_or_create_collection(collection_name)
    query_embedding = embed_text(query)

    where: dict[str, Any] | None = None
    if tag_filter:
        where = {"tags": {"$in": tag_filter}}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.warning("Tag-filtered query failed (%s), retrying without filter", exc)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

    chunks: list[dict[str, Any]] = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        relevance = max(0.0, 1.0 - float(dist))
        raw_tags = meta.get("tags", "")
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []
        chunks.append(
            {
                "chunk": doc,
                "source_document": meta.get("source_document", ""),
                "relevance_score": round(relevance, 4),
                "tags": tags,
            }
        )

    return chunks
