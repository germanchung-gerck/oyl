from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeBase, Document
from app.models.instruction import Instruction
from app.schemas.instruction import InstructionCreate
from app.services.orchestration_service import get_assistant
from app.services.rag_pipeline import RAGPipeline
from app.utils.errors import NotFoundError


def create_knowledge_base(db: Session, assistant_id: str, name: str, vector_db_id: str | None = None) -> KnowledgeBase:
    get_assistant(db, assistant_id)
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


def process_document(
    db: Session,
    doc_id: str,
    collection_name: str,
    pipeline: RAGPipeline | None = None,
) -> dict[str, Any]:
    """Run the full OCR → embed → tag → index pipeline for a single document.

    Updates the document's ``processed_status`` in the database and returns
    a summary dict with ``chunk_count`` and ``tags``.
    """
    doc = db.get(Document, doc_id)
    if not doc:
        raise NotFoundError(f"Document {doc_id} not found")

    if pipeline is None:
        pipeline = RAGPipeline()

    doc.processed_status = "processing"
    db.commit()

    try:
        with open(doc.file_path, "rb") as fh:
            content = fh.read()
    except OSError as exc:
        doc.processed_status = "failed"
        db.commit()
        raise RuntimeError(
            f"Cannot read file for document {doc.id} at '{doc.file_path}': {exc}"
        ) from exc

    try:
        result = pipeline.index_document(
            doc_id=doc.id,
            content=content,
            file_type=doc.file_type,
            collection_name=collection_name,
            source_name=doc.file_path,
        )
        doc.processed_status = "completed"
        db.commit()
        return result
    except Exception as exc:
        doc.processed_status = "failed"
        db.commit()
        raise exc


def get_knowledge_status(db: Session, assistant_id: str) -> dict[str, Any]:
    """Return processing status for all documents in the assistant's knowledge bases."""
    get_assistant(db, assistant_id)
    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.assistant_id == assistant_id).all()

    documents: list[dict[str, Any]] = []
    for kb in kbs:
        for doc in kb.documents:
            documents.append(
                {
                    "id": doc.id,
                    "file_path": doc.file_path,
                    "file_type": doc.file_type,
                    "processed_status": doc.processed_status,
                    "knowledge_base_id": doc.knowledge_base_id,
                }
            )

    status_counts: dict[str, int] = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
    for doc in documents:
        key = doc["processed_status"]
        status_counts[key] = status_counts.get(key, 0) + 1

    return {
        "assistant_id": assistant_id,
        "total": len(documents),
        "pending": status_counts.get("pending", 0),
        "completed": status_counts.get("completed", 0),
        "failed": status_counts.get("failed", 0),
        "documents": documents,
    }
