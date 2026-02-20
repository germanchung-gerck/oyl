from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeBase, Document
from app.models.instruction import Instruction
from app.schemas.instruction import InstructionCreate
from app.services.orchestration_service import get_assistant
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
