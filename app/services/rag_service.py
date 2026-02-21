"""RAG service: document processing pipeline (OCR → chunking → embedding → tagging)."""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.knowledge import KnowledgeBase, Document
from app.models.instruction import Instruction
from app.schemas.instruction import InstructionCreate
from app.services.deepseek_service import DeepSeekService
from app.services.tagging_service import generate_tags
from app.services.embedding_service import embed_and_store_chunks
from app.services.orchestration_service import get_assistant
from app.utils.errors import NotFoundError

logger = logging.getLogger(__name__)


def create_knowledge_base(db: Session, assistant_id: str, name: str, vector_db_id: str | None = None) -> KnowledgeBase:
    get_assistant(db, assistant_id)
    # Return existing KB if one already exists for this assistant
    existing = db.query(KnowledgeBase).filter(KnowledgeBase.assistant_id == assistant_id).first()
    if existing:
        return existing
    kb = KnowledgeBase(assistant_id=assistant_id, name=name, vector_db_id=vector_db_id)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


def add_document(
    db: Session,
    knowledge_base_id: str,
    file_path: str,
    file_type: str | None = None,
    raw_content: str | None = None,
) -> Document:
    kb = db.get(KnowledgeBase, knowledge_base_id)
    if not kb:
        raise NotFoundError(f"KnowledgeBase {knowledge_base_id} not found")
    doc = Document(
        knowledge_base_id=knowledge_base_id,
        file_path=file_path,
        file_type=file_type,
        raw_content=raw_content,
        processed_status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def upsert_instruction(db: Session, assistant_id: str, data: InstructionCreate) -> Instruction:
    get_assistant(db, assistant_id)
    instruction = (
        db.query(Instruction).filter(Instruction.assistant_id == assistant_id).first()
    )
    if instruction:
        instruction.system_prompt = data.system_prompt
    else:
        instruction = Instruction(assistant_id=assistant_id, system_prompt=data.system_prompt)
        db.add(instruction)
    db.commit()
    db.refresh(instruction)
    return instruction


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """Split *text* into overlapping chunks of *chunk_size* characters."""
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if overlap is None:
        overlap = settings.CHUNK_OVERLAP
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def process_document(
    db: Session,
    document_id: str,
    collection_name: str,
) -> dict[str, Any]:
    """
    Run the full RAG pipeline for a single document:
    1. OCR via DeepSeek-OCR (Ollama)
    2. Chunk text
    3. Tag each chunk (neural-chat:7b)
    4. Embed and store in Chroma
    Returns processing statistics.
    """
    doc = db.get(Document, document_id)
    if not doc:
        raise NotFoundError(f"Document {document_id} not found")

    start = time.time()
    doc.processed_status = "processing"
    db.commit()

    try:
        # 1. Extract text
        ocr = DeepSeekService()
        text = ocr.extract_text(doc.file_path)
        if not text and doc.raw_content:
            text = doc.raw_content

        # 2. Chunk
        chunks = chunk_text(text)
        if not chunks:
            doc.processed_status = "processed"
            db.commit()
            return {"chunks_created": 0, "tags_generated": 0, "processing_time_seconds": time.time() - start}

        # 3. Tag each chunk and build metadata
        source_name = doc.file_path.split("/")[-1]
        metadatas: list[dict[str, Any]] = []
        total_tags = 0
        for chunk in chunks:
            tags = generate_tags(chunk)
            total_tags += len(tags)
            metadatas.append(
                {
                    "source_document": source_name,
                    "document_id": doc.id,
                    "tags": ",".join(tags),
                }
            )

        # 4. Embed and store
        embed_and_store_chunks(
            collection_name=collection_name,
            chunks=chunks,
            metadatas=metadatas,
            id_prefix=f"{doc.id}_",
        )

        doc.processed_status = "processed"
        db.commit()

        elapsed = time.time() - start
        return {
            "chunks_created": len(chunks),
            "tags_generated": total_tags,
            "processing_time_seconds": round(elapsed, 2),
        }
    except Exception as exc:
        logger.error("Document processing failed for %s: %s", document_id, exc)
        doc.processed_status = "failed"
        db.commit()
        raise


def get_knowledge_status(db: Session, assistant_id: str) -> dict[str, Any]:
    """Return processing status and metrics for an assistant's knowledge base."""
    get_assistant(db, assistant_id)
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.assistant_id == assistant_id).first()
    if not kb:
        return {
            "assistant_id": assistant_id,
            "knowledge_base_id": None,
            "total_documents": 0,
            "processed_documents": 0,
            "pending_documents": 0,
            "total_chunks": 0,
            "embedding_model": settings.EMBEDDING_MODEL,
            "vector_store_collection": None,
        }

    docs = db.query(Document).filter(Document.knowledge_base_id == kb.id).all()
    processed = sum(1 for d in docs if d.processed_status == "processed")
    pending = sum(1 for d in docs if d.processed_status in ("pending", "processing"))

    return {
        "assistant_id": assistant_id,
        "knowledge_base_id": kb.id,
        "total_documents": len(docs),
        "processed_documents": processed,
        "pending_documents": pending,
        "total_chunks": 0,  # would query Chroma for exact count
        "embedding_model": settings.EMBEDDING_MODEL,
        "vector_store_collection": kb.vector_db_id,
    }

