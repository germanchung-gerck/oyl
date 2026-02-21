"""End-to-end RAG pipeline tests with mocked Ollama and Chroma services."""
from __future__ import annotations

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _create_tenant(client: TestClient) -> str:
    r = client.post("/api/v1/tenants", json={"name": "RAG Test Tenant"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create_workspace(client: TestClient, tenant_id: str) -> str:
    r = client.post(f"/api/v1/tenants/{tenant_id}/workspaces", json={"name": "RAG WS"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create_teammate(client: TestClient, workspace_id: str) -> str:
    r = client.post(f"/api/v1/workspaces/{workspace_id}/teammates", json={"name": "Bot"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create_assistant(client: TestClient, teammate_id: str) -> str:
    r = client.post(f"/api/v1/teammates/{teammate_id}/assistants", json={"name": "Asst"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Chunk text helper unit tests
# ---------------------------------------------------------------------------

def test_chunk_text_basic():
    from app.services.rag_service import chunk_text

    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_chunk_text_empty():
    from app.services.rag_service import chunk_text

    assert chunk_text("") == []


def test_chunk_text_short():
    from app.services.rag_service import chunk_text

    chunks = chunk_text("hello world", chunk_size=500, overlap=50)
    assert chunks == ["hello world"]


# ---------------------------------------------------------------------------
# Tagging service unit tests
# ---------------------------------------------------------------------------

def test_generate_tags_parses_csv():
    from app.services.tagging_service import _parse_tags

    raw = "refund, policy, customer, service"
    tags = _parse_tags(raw)
    assert tags == ["refund", "policy", "customer", "service"]


def test_generate_tags_parses_newlines():
    from app.services.tagging_service import _parse_tags

    raw = "refund\npolicy\ncustomer"
    tags = _parse_tags(raw)
    assert tags == ["refund", "policy", "customer"]


@patch("app.services.tagging_service.ollama")
def test_generate_tags_calls_ollama(mock_ollama):
    mock_ollama.generate.return_value = {"response": "refund, policy, customer"}
    from app.services.tagging_service import generate_tags

    tags = generate_tags("Test text about refunds", n=3)
    assert mock_ollama.generate.called
    assert len(tags) <= 3


# ---------------------------------------------------------------------------
# Reasoning steps extraction
# ---------------------------------------------------------------------------

def test_extract_reasoning_steps():
    from app.services.orchestration_service import _extract_reasoning_steps

    text = "<think>Step 1: analyze\nStep 2: conclude</think>Final answer here."
    steps, answer = _extract_reasoning_steps(text)
    assert "Step 1: analyze" in steps
    assert "Final answer here." in answer


def test_extract_reasoning_steps_no_think_block():
    from app.services.orchestration_service import _extract_reasoning_steps

    text = "Just a plain answer."
    steps, answer = _extract_reasoning_steps(text)
    assert steps == []
    assert answer == "Just a plain answer."


# ---------------------------------------------------------------------------
# Orchestration inference unit tests (mock Ollama)
# ---------------------------------------------------------------------------

@patch("app.services.orchestration_service.ollama")
def test_run_fast_inference(mock_ollama):
    mock_ollama.generate.return_value = {"response": "42 days is the refund window."}
    from app.services.orchestration_service import run_fast_inference

    chunks = [
        {"chunk": "Refund policy: 42 days.", "source_document": "policy.pdf", "tags": ["refund"]},
    ]
    result = run_fast_inference(chunks, "What is the refund window?")
    assert result["answer"] == "42 days is the refund window."
    assert result["model_used"] is not None
    assert result["processing_time_seconds"] >= 0


@patch("app.services.orchestration_service.ollama")
def test_run_reasoning_inference(mock_ollama):
    mock_ollama.generate.return_value = {
        "response": "<think>Step 1: Read context\nStep 2: Conclude</think>The answer is 42 days."
    }
    from app.services.orchestration_service import run_reasoning_inference

    chunks = [
        {"chunk": "Refund policy: 42 days.", "source_document": "policy.pdf", "tags": ["refund"]},
    ]
    result = run_reasoning_inference(chunks, "What is the refund window?")
    assert "42 days" in result["answer"]
    assert isinstance(result["reasoning_steps"], list)
    assert len(result["reasoning_steps"]) > 0


# ---------------------------------------------------------------------------
# Embedding service unit tests (mock Ollama + Chroma)
# ---------------------------------------------------------------------------

@patch("app.services.embedding_service.ollama")
def test_embed_text(mock_ollama):
    mock_ollama.embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}
    from app.services.embedding_service import embed_text

    vec = embed_text("hello world")
    assert vec == [0.1, 0.2, 0.3]


@patch("app.services.embedding_service._chroma_client")
@patch("app.services.embedding_service.ollama")
def test_embed_and_store_chunks(mock_ollama, mock_chroma_client):
    mock_ollama.embeddings.return_value = {"embedding": [0.1] * 768}
    mock_collection = MagicMock()
    mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

    from app.services.embedding_service import embed_and_store_chunks

    ids = embed_and_store_chunks(
        collection_name="test_col",
        chunks=["chunk one", "chunk two"],
        metadatas=[{"source_document": "a.txt", "tags": "tag1"}, {"source_document": "a.txt", "tags": "tag2"}],
    )
    assert len(ids) == 2
    assert mock_collection.upsert.called


# ---------------------------------------------------------------------------
# Retrieval service unit tests (mock Ollama + Chroma)
# ---------------------------------------------------------------------------

@patch("app.services.retrieval_service.get_or_create_collection")
@patch("app.services.retrieval_service.embed_text")
def test_retrieve_chunks(mock_embed, mock_get_collection):
    mock_embed.return_value = [0.1] * 768
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["Chunk about refund policy."]],
        "metadatas": [[{"source_document": "policy.pdf", "tags": "refund,policy"}]],
        "distances": [[0.1]],
    }
    mock_get_collection.return_value = mock_collection

    from app.services.retrieval_service import retrieve_chunks

    results = retrieve_chunks("test_col", "refund", top_k=5)
    assert len(results) == 1
    assert results[0]["source_document"] == "policy.pdf"
    assert "refund" in results[0]["tags"]
    assert results[0]["relevance_score"] == pytest.approx(0.9, abs=0.01)


# ---------------------------------------------------------------------------
# RAG API endpoint tests
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.rag.process_document")
@patch("app.services.embedding_service.embed_and_store_chunks")
def test_upload_document_txt(mock_embed, mock_process, client):
    """Upload a plain text document and check response."""
    mock_process.return_value = {
        "chunks_created": 3,
        "tags_generated": 9,
        "processing_time_seconds": 1.5,
    }

    tenant_id = _create_tenant(client)
    ws_id = _create_workspace(client, tenant_id)
    tm_id = _create_teammate(client, ws_id)
    asst_id = _create_assistant(client, tm_id)

    file_content = b"This is a test document about refund policies." * 10
    response = client.post(
        f"/api/v1/assistants/{asst_id}/knowledge/upload",
        files={"file": ("test_policy.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["chunks_created"] == 3
    assert data["tags_generated"] == 9
    assert data["status"] == "processed"
    assert data["file_name"] == "test_policy.txt"


def test_upload_document_unsupported_type(client):
    """Upload a file with unsupported extension should return 400."""
    tenant_id = _create_tenant(client)
    ws_id = _create_workspace(client, tenant_id)
    tm_id = _create_teammate(client, ws_id)
    asst_id = _create_assistant(client, tm_id)

    response = client.post(
        f"/api/v1/assistants/{asst_id}/knowledge/upload",
        files={"file": ("bad_file.xyz", io.BytesIO(b"data"), "application/octet-stream")},
    )
    assert response.status_code == 400


def test_upload_document_unknown_assistant(client):
    """Upload to non-existent assistant should return 404."""
    response = client.post(
        "/api/v1/assistants/nonexistent-id/knowledge/upload",
        files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
    )
    assert response.status_code == 404


def test_knowledge_status_no_kb(client):
    """Status endpoint returns empty stats when no KB exists."""
    tenant_id = _create_tenant(client)
    ws_id = _create_workspace(client, tenant_id)
    tm_id = _create_teammate(client, ws_id)
    asst_id = _create_assistant(client, tm_id)

    response = client.get(f"/api/v1/assistants/{asst_id}/knowledge/status")
    assert response.status_code == 200
    data = response.json()
    assert data["total_documents"] == 0
    assert data["assistant_id"] == asst_id


def test_knowledge_status_not_found(client):
    response = client.get("/api/v1/assistants/unknown-id/knowledge/status")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Orchestration query endpoint tests
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.orchestration.generate_query_tags")
@patch("app.api.v1.endpoints.orchestration.retrieve_chunks")
@patch("app.api.v1.endpoints.orchestration.run_fast_inference")
def test_query_fast_mode(mock_inference, mock_retrieve, mock_tags, client):
    mock_tags.return_value = ["refund", "policy"]
    mock_retrieve.return_value = [
        {"chunk": "42 days refund window.", "source_document": "policy.pdf", "relevance_score": 0.9, "tags": ["refund"]}
    ]
    mock_inference.return_value = {
        "answer": "The refund window is 42 days.",
        "reasoning_steps": None,
        "model_used": "qwen3:7b",
        "processing_time_seconds": 1.2,
    }

    tenant_id = _create_tenant(client)
    ws_id = _create_workspace(client, tenant_id)
    tm_id = _create_teammate(client, ws_id)
    asst_id = _create_assistant(client, tm_id)

    response = client.post(
        f"/api/v1/teammates/{tm_id}/query",
        json={"query": "What is the refund window?", "inference_mode": "fast"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["inference_mode"] == "fast"
    assert data["model_used"] == "qwen3:7b"
    assert data["answer"] == "The refund window is 42 days."
    assert len(data["sources"]) == 1


@patch("app.api.v1.endpoints.orchestration.generate_query_tags")
@patch("app.api.v1.endpoints.orchestration.retrieve_chunks")
@patch("app.api.v1.endpoints.orchestration.run_reasoning_inference")
def test_query_reasoning_mode(mock_inference, mock_retrieve, mock_tags, client):
    mock_tags.return_value = ["refund"]
    mock_retrieve.return_value = [
        {"chunk": "42 days refund window.", "source_document": "policy.pdf", "relevance_score": 0.95, "tags": ["refund"]}
    ]
    mock_inference.return_value = {
        "answer": "After careful reasoning, the refund window is 42 days.",
        "reasoning_steps": ["Step 1: read policy", "Step 2: identify window"],
        "model_used": "deepseek-r1:8b",
        "processing_time_seconds": 11.0,
    }

    tenant_id = _create_tenant(client)
    ws_id = _create_workspace(client, tenant_id)
    tm_id = _create_teammate(client, ws_id)
    asst_id = _create_assistant(client, tm_id)

    response = client.post(
        f"/api/v1/teammates/{tm_id}/query",
        json={"query": "What is the refund window?", "inference_mode": "reasoning"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["inference_mode"] == "reasoning"
    assert data["model_used"] == "deepseek-r1:8b"
    assert data["reasoning_steps"] is not None
    assert len(data["reasoning_steps"]) > 0


@patch("app.api.v1.endpoints.orchestration.generate_query_tags")
@patch("app.api.v1.endpoints.orchestration.retrieve_chunks")
def test_query_empty_knowledge_base(mock_retrieve, mock_tags, client):
    mock_tags.return_value = []
    mock_retrieve.return_value = []

    tenant_id = _create_tenant(client)
    ws_id = _create_workspace(client, tenant_id)
    tm_id = _create_teammate(client, ws_id)
    asst_id = _create_assistant(client, tm_id)

    response = client.post(
        f"/api/v1/teammates/{tm_id}/query",
        json={"query": "Something not in KB", "inference_mode": "fast"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "No relevant information" in data["answer"]
    assert data["sources"] == []


def test_query_teammate_not_found(client):
    response = client.post(
        "/api/v1/teammates/nonexistent-id/query",
        json={"query": "test", "inference_mode": "fast"},
    )
    assert response.status_code == 404


def test_query_no_assistant_for_teammate(client):
    """Teammate without assistant should 404."""
    tenant_id = _create_tenant(client)
    ws_id = _create_workspace(client, tenant_id)
    tm_id = _create_teammate(client, ws_id)
    # No assistant created

    response = client.post(
        f"/api/v1/teammates/{tm_id}/query",
        json={"query": "test", "inference_mode": "fast"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DeepSeek service unit tests
# ---------------------------------------------------------------------------

def test_deepseek_extract_text_txt(tmp_path):
    """Text files are read directly without Ollama."""
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Hello from text file", encoding="utf-8")

    from app.services.deepseek_service import DeepSeekService

    svc = DeepSeekService()
    text = svc.extract_text(str(txt_file))
    assert text == "Hello from text file"


@patch("app.services.deepseek_service.ollama")
def test_deepseek_extract_text_image(mock_ollama, tmp_path):
    """Image files trigger OCR via Ollama."""
    mock_ollama.generate.return_value = {"response": "Extracted image text"}

    # Create a minimal PNG-like file (just needs to exist)
    img_file = tmp_path / "sample.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    from app.services.deepseek_service import DeepSeekService

    svc = DeepSeekService(model="deepseek-ocr:latest")
    text = svc.extract_text(str(img_file))
    assert text == "Extracted image text"
    assert mock_ollama.generate.called


# ---------------------------------------------------------------------------
# Process document pipeline (mock OCR, tagging, embedding)
# ---------------------------------------------------------------------------

@patch("app.services.rag_service.embed_and_store_chunks")
@patch("app.services.rag_service.generate_tags")
@patch("app.services.rag_service.DeepSeekService")
def test_process_document_pipeline(mock_ds_cls, mock_tags, mock_embed, client, db_session):
    """Test the full process_document pipeline with mocked external calls."""
    mock_ds_cls.return_value.extract_text.return_value = "Sample text. " * 50
    mock_tags.return_value = ["sample", "text", "test"]
    mock_embed.return_value = ["chunk-id-1", "chunk-id-2"]

    # Set up DB objects
    tenant_id = _create_tenant(client)
    ws_id = _create_workspace(client, tenant_id)
    tm_id = _create_teammate(client, ws_id)
    asst_id = _create_assistant(client, tm_id)

    from app.services.rag_service import create_knowledge_base, add_document, process_document
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Sample text. " * 50)
        tmp_path = f.name

    kb = create_knowledge_base(db_session, asst_id, name="test-kb")
    doc = add_document(db_session, kb.id, file_path=tmp_path, file_type="text/plain")

    stats = process_document(db_session, doc.id, collection_name=f"assistant_{asst_id}")

    assert stats["chunks_created"] > 0
    assert stats["tags_generated"] > 0
    assert stats["processing_time_seconds"] >= 0

    # Verify document status updated
    db_session.refresh(doc)
    assert doc.processed_status == "processed"
