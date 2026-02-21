# RAG Pipeline Implementation Guide

## Overview

This guide covers the Retrieval-Augmented Generation (RAG) pipeline integrated into the Oyl platform. The pipeline supports document ingestion with OCR, intelligent tagging, vector search, and dual-mode LLM inference — all running locally via Ollama.

---

## Architecture

### Document Upload Flow

```
User uploads PDF/image/text
      │
      ▼
DeepSeek-OCR (Ollama) ─── Extract text
      │
      ▼
chunk_text() ─── 500-char overlapping chunks
      │
      ▼
neural-chat:7b (Ollama) ─── Generate 3-5 tags per chunk
      │
      ▼
nomic-embed-text (Ollama) ─── 768-dim embeddings
      │
      ▼
ChromaDB ─── Store {chunk, embedding, tags, metadata}
```

### Query Flow

```
User submits query + inference_mode
      │
      ▼
nomic-embed-text ─── Embed query
      │
      ▼
neural-chat:7b ─── Generate query tags
      │
      ▼
ChromaDB ─── Semantic search with tag filter (top-K chunks)
      │
      ▼
  ┌───┴───┐
  │       │
reasoning  fast
  │       │
deepseek   qwen3
 r1:8b    :7b
  │       │
  └───┬───┘
      │
      ▼
Return {answer, sources, reasoning_steps, model, timing}
```

---

## Models

| Purpose | Model | Size |
|---------|-------|------|
| OCR | deepseek-ocr:latest | 6.7GB |
| Embeddings | nomic-embed-text:latest | 274MB |
| Tagging | neural-chat:7b | 4.1GB |
| Reasoning | deepseek-r1:8b | 5.2GB |
| Fast | qwen3:7b | 4.7GB |

---

## Setup

### Prerequisites

- Ollama installed and running at `http://localhost:11434`
- ChromaDB running at `localhost:8000`
- PostgreSQL running

### Install Models

```bash
ollama pull deepseek-ocr:latest
ollama pull nomic-embed-text:latest
ollama pull neural-chat:7b
ollama pull deepseek-r1:8b
ollama pull qwen3:7b
```

### Configuration (`.env`)

```env
OLLAMA_BASE_URL=http://localhost:11434
OCR_MODEL=deepseek-ocr:latest
EMBEDDING_MODEL=nomic-embed-text:latest
TAGGING_MODEL=neural-chat:7b
REASONING_MODEL=deepseek-r1:8b
FAST_MODEL=qwen3:7b
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_CHUNKS=5
TAGS_PER_CHUNK=3
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

---

## API Endpoints

### Upload Document with OCR

```
POST /api/v1/assistants/{assistant_id}/knowledge/upload
Content-Type: multipart/form-data

file: <binary>
```

Supported file types: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp`, `.txt`, `.md`, `.csv`  
Max file size: 50MB

**Response:**
```json
{
  "document_id": "uuid",
  "knowledge_base_id": "uuid",
  "file_name": "policy.pdf",
  "file_type": "application/pdf",
  "chunks_created": 12,
  "tags_generated": 36,
  "processing_time_seconds": 8.4,
  "status": "processed"
}
```

### Batch Process Documents

```
POST /api/v1/assistants/{assistant_id}/knowledge/process-batch
Content-Type: application/json

{
  "document_ids": ["uuid1", "uuid2"]
}
```

### Knowledge Base Status

```
GET /api/v1/assistants/{assistant_id}/knowledge/status
```

**Response:**
```json
{
  "assistant_id": "uuid",
  "knowledge_base_id": "uuid",
  "total_documents": 5,
  "processed_documents": 4,
  "pending_documents": 1,
  "total_chunks": 0,
  "embedding_model": "nomic-embed-text:latest",
  "vector_store_collection": null
}
```

### Query with Dual-Mode Inference

```
POST /api/v1/teammates/{teammate_id}/query
Content-Type: application/json

{
  "query": "What is the refund policy?",
  "inference_mode": "reasoning",
  "top_k": 5
}
```

**inference_mode values:**
- `"fast"` — qwen3:7b, ~3-5 seconds, concise answers
- `"reasoning"` — deepseek-r1:8b, ~10-15 seconds, step-by-step reasoning

**Response:**
```json
{
  "query": "What is the refund policy?",
  "inference_mode": "reasoning",
  "answer": "Based on the documents...",
  "reasoning_steps": ["Step 1: ...", "Step 2: ..."],
  "sources": [
    {
      "chunk": "...",
      "source_document": "policy.pdf",
      "relevance_score": 0.95,
      "tags": ["refund", "policy"]
    }
  ],
  "model_used": "deepseek-r1:8b",
  "processing_time_seconds": 12.3,
  "inference_mode_used": "reasoning"
}
```

---

## Service Layer

### `app/services/embedding_service.py`
- `embed_text(text)` — Generate embedding vector via nomic-embed-text
- `embed_and_store_chunks(collection, chunks, metadatas)` — Embed and store in Chroma
- `get_or_create_collection(name)` — Get/create Chroma collection

### `app/services/tagging_service.py`
- `generate_tags(text, n)` — Generate n tags via neural-chat:7b
- `generate_query_tags(query)` — Generate tags for query-time filtering

### `app/services/retrieval_service.py`
- `retrieve_chunks(collection, query, top_k, tag_filter)` — Semantic search with optional tag filtering

### `app/services/deepseek_service.py`
- `DeepSeekService.extract_text(file_path)` — OCR extraction (text, image, PDF)

### `app/services/rag_service.py`
- `chunk_text(text, chunk_size, overlap)` — Split text into overlapping chunks
- `process_document(db, document_id, collection_name)` — Full OCR→chunk→tag→embed pipeline
- `get_knowledge_status(db, assistant_id)` — Document processing metrics

### `app/services/orchestration_service.py`
- `run_reasoning_inference(chunks, query)` — deepseek-r1:8b with step-by-step reasoning
- `run_fast_inference(chunks, query)` — qwen3:7b concise inference

---

## Testing

```bash
pytest tests/test_rag_pipeline.py -v
```

All external dependencies (Ollama, ChromaDB) are mocked in tests.

---

## Performance Metrics (M4 MacBook Pro)

| Operation | Approximate Time |
|-----------|-----------------|
| OCR per page (PDF) | 10-30 seconds |
| Embedding per chunk | < 1 second |
| Tagging per chunk | 2-3 seconds |
| Fast inference (qwen3:7b) | 3-5 seconds |
| Reasoning inference (deepseek-r1:8b) | 10-15 seconds |

---

## Troubleshooting

### Ollama not reachable
Verify Ollama is running: `ollama serve`  
Check endpoint in config: `OLLAMA_BASE_URL=http://localhost:11434`

### ChromaDB connection error
Ensure Chroma is running: `docker compose up chromadb`  
Check `CHROMA_HOST` and `CHROMA_PORT` settings.

### PDF processing fails
Ensure `poppler` is installed: `brew install poppler` (macOS)  
pdf2image requires poppler utilities.

### Model not found
Pull the model: `ollama pull <model-name>`  
Verify with: `ollama list`

### Tag filtering returns no results
Tag filtering degrades gracefully — if the filtered query returns nothing, it retries without the filter. Check logs for `Tag-filtered query failed` messages.
