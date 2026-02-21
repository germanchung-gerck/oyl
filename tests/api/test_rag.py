"""Integration tests for the RAG pipeline endpoints.

Ollama and Chroma are mocked so that tests run without external services.
"""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers: create database fixtures
# ---------------------------------------------------------------------------

def _make_tenant(client):
    r = client.post("/api/v1/tenants", json={"name": "RAG Tenant"})
    assert r.status_code == 201
    return r.json()["id"]


def _make_workspace(client, tenant_id):
    r = client.post(f"/api/v1/tenants/{tenant_id}/workspaces", json={"name": "RAG WS"})
    assert r.status_code == 201
    return r.json()["id"]


def _make_teammate(client, workspace_id):
    r = client.post(
        f"/api/v1/workspaces/{workspace_id}/teammates",
        json={"name": "RAG Teammate"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _make_assistant(client, teammate_id):
    r = client.post(
        f"/api/v1/teammates/{teammate_id}/assistants",
        json={"name": "RAG Assistant"},
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Chroma mock factory
# ---------------------------------------------------------------------------

def _mock_chroma_collection():
    col = MagicMock()
    col.add = MagicMock()
    col.query = MagicMock(
        return_value={
            "documents": [["This is a relevant chunk about AI."]],
            "metadatas": [[{"doc_id": "d1", "source": "test.txt", "tags": "ai,ml", "file_type": "text/plain", "chunk_index": 0}]],
            "distances": [[0.1]],
        }
    )
    return col


# ---------------------------------------------------------------------------
# Tests: knowledge upload
# ---------------------------------------------------------------------------

class TestKnowledgeUpload:
    def test_upload_text_document(self, client):
        tenant_id = _make_tenant(client)
        workspace_id = _make_workspace(client, tenant_id)
        teammate_id = _make_teammate(client, workspace_id)
        assistant_id = _make_assistant(client, teammate_id)

        content = b"Hello world document content for RAG testing."
        response = client.post(
            f"/api/v1/assistants/{assistant_id}/knowledge/upload",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["processed_status"] == "pending"
        assert data["file_type"] == "text/plain"

    def test_upload_unknown_assistant_returns_404(self, client):
        content = b"some content"
        response = client.post(
            "/api/v1/assistants/nonexistent-id/knowledge/upload",
            files={"file": ("doc.txt", io.BytesIO(content), "text/plain")},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: knowledge status
# ---------------------------------------------------------------------------

class TestKnowledgeStatus:
    def test_status_returns_document_list(self, client):
        tenant_id = _make_tenant(client)
        workspace_id = _make_workspace(client, tenant_id)
        teammate_id = _make_teammate(client, workspace_id)
        assistant_id = _make_assistant(client, teammate_id)

        content = b"Status test document"
        client.post(
            f"/api/v1/assistants/{assistant_id}/knowledge/upload",
            files={"file": ("status_test.txt", io.BytesIO(content), "text/plain")},
        )

        response = client.get(f"/api/v1/assistants/{assistant_id}/knowledge/status")
        assert response.status_code == 200
        data = response.json()
        assert data["assistant_id"] == assistant_id
        assert data["total"] >= 1
        assert "pending" in data

    def test_status_unknown_assistant_returns_404(self, client):
        response = client.get("/api/v1/assistants/nonexistent/knowledge/status")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: batch process
# ---------------------------------------------------------------------------

class TestBatchProcess:
    def _setup(self, client):
        tenant_id = _make_tenant(client)
        workspace_id = _make_workspace(client, tenant_id)
        teammate_id = _make_teammate(client, workspace_id)
        assistant_id = _make_assistant(client, teammate_id)
        return assistant_id

    @patch("app.api.v1.endpoints.knowledge.process_document")
    @patch("app.api.v1.endpoints.knowledge.get_knowledge_status")
    def test_batch_process_all_pending(
        self, mock_status, mock_process, client
    ):
        assistant_id = self._setup(client)

        mock_status.return_value = {
            "assistant_id": assistant_id,
            "total": 0,
            "pending": 0,
            "completed": 0,
            "failed": 0,
            "documents": [],
        }

        response = client.post(
            f"/api/v1/assistants/{assistant_id}/knowledge/process-batch",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert "processed" in data
        assert "failed" in data
        assert "details" in data

    @patch("app.api.v1.endpoints.knowledge.process_document")
    @patch("app.api.v1.endpoints.knowledge.get_knowledge_status")
    def test_batch_process_returns_404_for_unknown_assistant(
        self, mock_status, mock_process, client
    ):
        from app.utils.errors import NotFoundError
        mock_status.side_effect = NotFoundError("not found")

        response = client.post(
            "/api/v1/assistants/nonexistent/knowledge/process-batch",
            json={},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: query endpoint (dual-mode)
# ---------------------------------------------------------------------------

class TestTeammateQuery:
    def _setup(self, client):
        tenant_id = _make_tenant(client)
        workspace_id = _make_workspace(client, tenant_id)
        teammate_id = _make_teammate(client, workspace_id)
        return teammate_id

    @patch("app.api.v1.endpoints.orchestration.RAGPipeline")
    def test_fast_mode_query(self, MockPipeline, client):
        teammate_id = self._setup(client)

        mock_pipeline = MagicMock()
        mock_pipeline.query.return_value = {
            "answer": "The answer is 42.",
            "mode": "fast",
            "model": "qwen2.5:7b",
            "sources": ["doc1.txt"],
            "query_tags": ["ai", "ml"],
            "processing_time_ms": 250,
        }
        MockPipeline.return_value = mock_pipeline

        response = client.post(
            f"/api/v1/teammates/{teammate_id}/query",
            json={"query": "What is the answer?", "mode": "fast"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "The answer is 42."
        assert data["mode"] == "fast"
        assert data["model"] == "qwen2.5:7b"
        assert data["teammate_id"] == teammate_id
        assert data["query"] == "What is the answer?"

    @patch("app.api.v1.endpoints.orchestration.RAGPipeline")
    def test_reasoning_mode_query(self, MockPipeline, client):
        teammate_id = self._setup(client)

        mock_pipeline = MagicMock()
        mock_pipeline.query.return_value = {
            "answer": "Step 1: ... Step 2: ... Therefore, the answer is 42.",
            "mode": "reasoning",
            "model": "deepseek-r1:7b",
            "sources": ["doc1.txt"],
            "query_tags": ["reasoning"],
            "processing_time_ms": 3000,
        }
        MockPipeline.return_value = mock_pipeline

        response = client.post(
            f"/api/v1/teammates/{teammate_id}/query",
            json={"query": "Explain step by step.", "mode": "reasoning"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "reasoning"
        assert data["model"] == "deepseek-r1:7b"

    @patch("app.api.v1.endpoints.orchestration.RAGPipeline")
    def test_invalid_mode_defaults_to_fast(self, MockPipeline, client):
        teammate_id = self._setup(client)

        mock_pipeline = MagicMock()
        mock_pipeline.query.return_value = {
            "answer": "Some answer.",
            "mode": "fast",
            "model": "qwen2.5:7b",
            "sources": [],
            "query_tags": [],
            "processing_time_ms": 100,
        }
        MockPipeline.return_value = mock_pipeline

        response = client.post(
            f"/api/v1/teammates/{teammate_id}/query",
            json={"query": "Test?", "mode": "invalid-mode"},
        )
        assert response.status_code == 200
        # mode passed to pipeline should be "fast"
        _, call_kwargs = mock_pipeline.query.call_args
        assert call_kwargs["mode"] == "fast"

    def test_query_unknown_teammate_returns_404(self, client):
        response = client.post(
            "/api/v1/teammates/nonexistent/query",
            json={"query": "test"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: RAG pipeline unit tests
# ---------------------------------------------------------------------------

class TestRAGPipelineUnit:
    """Unit tests for the RAG pipeline that mock Ollama + Chroma."""

    def _make_pipeline(self):
        from app.services.rag_pipeline import RAGPipeline
        from app.services.ollama_client import OllamaClient

        mock_ollama = MagicMock(spec=OllamaClient)
        mock_ollama.generate.return_value = "ai, machine learning, data"
        mock_ollama.embed.return_value = [0.1] * 768

        pipeline = RAGPipeline(ollama=mock_ollama)
        return pipeline, mock_ollama

    def test_chunk_text_basic(self):
        from app.services.rag_pipeline import chunk_text
        text = "a" * 2500
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 3
        assert len(chunks[0]) == 1000
        assert chunks[1] == text[800:1800]

    def test_chunk_text_empty(self):
        from app.services.rag_pipeline import chunk_text
        assert chunk_text("", chunk_size=1000, chunk_overlap=200) == []

    def test_chunk_text_shorter_than_chunk_size(self):
        from app.services.rag_pipeline import chunk_text
        text = "short text"
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)
        assert chunks == [text]

    def test_extract_text_plain(self):
        pipeline, _ = self._make_pipeline()
        content = b"Hello RAG world"
        result = pipeline.extract_text(content, "text/plain")
        assert result == "Hello RAG world"

    def test_extract_text_binary_calls_ollama(self):
        pipeline, mock_ollama = self._make_pipeline()
        mock_ollama.generate.return_value = "Extracted PDF text"
        content = b"%PDF-1.4 binary content"
        result = pipeline.extract_text(content, "application/pdf")
        assert result == "Extracted PDF text"
        mock_ollama.generate.assert_called_once()

    def test_tag_text(self):
        pipeline, mock_ollama = self._make_pipeline()
        mock_ollama.generate.return_value = "  AI, machine learning, NLP "
        tags = pipeline.tag_text("Some text about AI and ML")
        assert "ai" in tags
        assert "machine learning" in tags

    def test_tag_text_limits_to_five(self):
        pipeline, mock_ollama = self._make_pipeline()
        mock_ollama.generate.return_value = "a, b, c, d, e, f, g"
        tags = pipeline.tag_text("text")
        assert len(tags) <= 5

    @patch("app.services.rag_pipeline.chromadb.HttpClient")
    def test_index_document(self, MockChromaClient):
        pipeline, mock_ollama = self._make_pipeline()
        mock_col = _mock_chroma_collection()
        MockChromaClient.return_value.get_or_create_collection.return_value = mock_col
        pipeline._chroma_client = MockChromaClient.return_value

        result = pipeline.index_document(
            doc_id="doc1",
            content=b"Test document content for indexing",
            file_type="text/plain",
            collection_name="test_col",
            source_name="test.txt",
        )
        assert result["chunk_count"] >= 1
        assert isinstance(result["tags"], list)
        mock_col.add.assert_called_once()

    @patch("app.services.rag_pipeline.chromadb.HttpClient")
    def test_query_fast_mode(self, MockChromaClient):
        pipeline, mock_ollama = self._make_pipeline()
        mock_col = _mock_chroma_collection()
        MockChromaClient.return_value.get_or_create_collection.return_value = mock_col
        pipeline._chroma_client = MockChromaClient.return_value

        mock_ollama.generate.side_effect = [
            "ai, ml",  # tag_text
            "The answer is 42.",  # _infer_fast
        ]
        mock_ollama.embed.return_value = [0.1] * 768

        result = pipeline.query("What is AI?", "test_col", mode="fast")
        assert result["mode"] == "fast"
        assert "answer" in result
        assert "processing_time_ms" in result
        assert isinstance(result["sources"], list)

    @patch("app.services.rag_pipeline.chromadb.HttpClient")
    def test_query_reasoning_mode(self, MockChromaClient):
        pipeline, mock_ollama = self._make_pipeline()
        mock_col = _mock_chroma_collection()
        MockChromaClient.return_value.get_or_create_collection.return_value = mock_col
        pipeline._chroma_client = MockChromaClient.return_value

        mock_ollama.generate.side_effect = [
            "ai, ml",  # tag_text for query
            "Step-by-step answer.",  # _infer_reasoning chunk
        ]
        mock_ollama.embed.return_value = [0.1] * 768

        result = pipeline.query("Explain AI step by step.", "test_col", mode="reasoning")
        assert result["mode"] == "reasoning"
        assert "answer" in result

    @patch("app.services.rag_pipeline.chromadb.HttpClient")
    def test_query_no_results_returns_empty_answer(self, MockChromaClient):
        pipeline, mock_ollama = self._make_pipeline()
        mock_col = MagicMock()
        mock_col.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        MockChromaClient.return_value.get_or_create_collection.return_value = mock_col
        pipeline._chroma_client = MockChromaClient.return_value

        mock_ollama.generate.return_value = "ai"
        mock_ollama.embed.return_value = [0.1] * 768

        result = pipeline.query("Obscure question", "empty_col", mode="fast")
        assert "No relevant documents" in result["answer"]
