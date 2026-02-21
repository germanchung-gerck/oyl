# Architecture

## Overview

OYL is a multi-tenant Retrieval-Augmented Generation (RAG) platform built with FastAPI. Each tenant can have multiple workspaces, each workspace hosts teammates (AI agents), and each teammate owns assistants with associated knowledge bases and instructions.

The platform enables organizations to:
- Isolate data and configurations per customer (multi-tenancy)
- Organize work with workspaces (departments / projects)
- Create AI agents (teammates) that orchestrate one or more assistants
- Upload and process documents (via DeepSeek-OCR) to populate per-assistant knowledge bases
- Route user queries intelligently across multiple LLM backends

---

## High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                            Clients                                   │
│  (Web browsers, mobile apps, CLI tools, third-party integrations)    │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  HTTPS / REST
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                              │
│  ┌───────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │
│  │ Tenant Context│  │  JWT Auth        │  │  CORS Middleware      │  │
│  │ Middleware    │  │  Middleware       │  │                      │  │
│  └───────┬───────┘  └────────┬────────┘  └──────────────────────┘  │
│          │                   │                                       │
│          └──────────┬────────┘                                       │
│                     ▼                                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   API Router  /api/v1                        │    │
│  │  /tenants  /workspaces  /teammates  /assistants              │    │
│  │  /knowledge               /orchestration                     │    │
│  └────────────────────────┬────────────────────────────────────┘    │
│                           │                                          │
│  ┌────────────────────────▼────────────────────────────────────┐    │
│  │                    Services Layer                            │    │
│  │  tenant_service  workspace_service  orchestration_service    │    │
│  │  rag_service     deepseek_service                            │    │
│  └──┬─────────────────────┬──────────────────┬─────────────────┘    │
└─────┼─────────────────────┼──────────────────┼─────────────────────┘
      │                     │                  │
      ▼                     ▼                  ▼
┌──────────┐        ┌──────────────┐   ┌──────────────┐
│PostgreSQL│        │  ChromaDB    │   │  Redis       │
│  (ORM:   │        │  (Vector DB) │   │  (Cache /    │
│SQLAlchemy│        │              │   │   Sessions)  │
│   2.x)   │        │              │   │              │
└──────────┘        └──────────────┘   └──────────────┘
                          ▲
                          │ embed & retrieve
                    ┌─────┴──────┐
                    │ DeepSeek   │
                    │ OCR / LLM  │
                    │  (External)│
                    └────────────┘
```

---

## Component Descriptions

### FastAPI Application (`app/main.py`)

The core web framework. Provides:
- Automatic OpenAPI / Swagger docs at `/docs` and `/redoc`
- Async-friendly endpoint handlers
- Dependency injection (database sessions, auth)
- Health check endpoint at `GET /health`

### TenantContextMiddleware (`app/middleware/tenant_context.py`)

Reads the `X-Tenant-ID` request header and stores it on `request.state.tenant_id`. All downstream services use this value to scope database queries to the correct tenant.

### JWT Auth Middleware (`app/middleware/auth.py`)

Validates Bearer tokens in the `Authorization` header using `python-jose`. Decoded claims are stored on `request.state` for use by endpoint handlers.

### API Router (`app/api/v1/router.py`)

Registers all versioned endpoint modules under the `/api/v1` prefix. API versioning is managed by URL path (`/api/v1`, `/api/v2`, …).

### Services Layer (`app/services/`)

| Service | Responsibility |
|---------|----------------|
| `tenant_service` | CRUD for tenants |
| `workspace_service` | CRUD for workspaces, validates tenant ownership |
| `orchestration_service` | CRUD for teammates and assistants, query routing |
| `rag_service` | Knowledge base and document management, vector upsert |
| `deepseek_service` | OCR extraction and LLM calls via DeepSeek API |

### PostgreSQL 15

Primary relational store. All entities (tenants → workspaces → teammates → assistants → knowledge bases → documents / instructions) are persisted here. Row-level tenant isolation is enforced in the services layer.

### ChromaDB (Vector Store)

Stores document embeddings for semantic search. Each knowledge base maps to a ChromaDB collection identified by `knowledge_bases.vector_db_id`. Similarity queries are issued during RAG retrieval.

### Redis 7

Used for:
- Session / token caching
- Rate-limiting counters
- Caching frequently read configuration (e.g., tenant metadata)

### DeepSeek-OCR / LLM (External)

External API that provides:
- **OCR**: Extracts text from uploaded PDFs, images, and other binary files
- **LLM inference**: Generates answers from retrieved document chunks

---

## Data Flow Diagrams

### Document Upload & Processing

```
Client
  │  POST /assistants/{id}/knowledge/upload
  │  (multipart/form-data)
  ▼
Knowledge Endpoint
  │
  ├─ create_knowledge_base()  →  PostgreSQL (knowledge_bases row)
  │
  ├─ Save raw bytes to /tmp/oyl_uploads/
  │
  ├─ decode text content (UTF-8 / DeepSeek-OCR for binary)
  │
  ├─ add_document()  →  PostgreSQL (documents row, status=pending)
  │
  └─ [Future: Celery task] embed chunks  →  ChromaDB collection
```

### Query / RAG Flow

```
Client
  │  POST /teammates/{id}/query  { "query": "..." }
  ▼
Orchestration Endpoint
  │
  ├─ get_teammate()  →  validate tenant / workspace ownership
  │
  ├─ load orchestration_config (which assistants, routing strategy)
  │
  ├─ for each assistant:
  │     ├─ embed query  →  ChromaDB similarity search
  │     ├─ retrieve top-k document chunks
  │     └─ call DeepSeek LLM with [system_prompt + chunks + query]
  │
  └─ merge / rank responses  →  return to client
```

---

## Multi-Tenancy Approach

OYL uses an **application-level row scoping** strategy (sometimes called "shared database, shared schema with tenant_id discriminator"):

1. Every top-level entity row in PostgreSQL carries a `tenant_id` foreign key.
2. The `TenantContextMiddleware` extracts the tenant identifier from the `X-Tenant-ID` request header.
3. Service functions receive `tenant_id` and include it in all `WHERE` clauses to prevent cross-tenant data access.
4. Cascade deletes ensure that removing a tenant purges all subordinate data automatically.

### Why this approach?

| Approach | Pros | Cons |
|----------|------|------|
| Separate DB per tenant | Strongest isolation | High ops overhead |
| Separate schema per tenant | Good isolation | Schema migration complexity |
| **Shared schema + tenant_id** ✓ | Simple, low overhead | Requires diligent query scoping |

The current implementation chooses simplicity (shared schema + tenant_id) and enforces isolation at the service layer. A future enhancement can add PostgreSQL Row-Level Security (RLS) policies as a second enforcement layer.

### Row-Level Security (Future Enhancement)

```sql
-- Enable RLS on a table
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- Policy: users may only see rows matching their tenant
CREATE POLICY tenant_isolation ON workspaces
    USING (tenant_id = current_setting('app.current_tenant_id'));

-- Application sets the config at the start of each transaction
SET LOCAL app.current_tenant_id = '<uuid>';
```

---

## Security & Isolation Strategy

| Concern | Implementation |
|---------|----------------|
| Authentication | JWT Bearer tokens (HS256, configurable expiry) |
| Tenant isolation | `X-Tenant-ID` header + service-layer query scoping |
| Transport security | HTTPS (TLS termination at load balancer / reverse proxy) |
| Secret management | Environment variables (never hardcoded) |
| CORS | Configurable `allow_origins` list (default `*` for dev) |
| File uploads | Saved to `/tmp/oyl_uploads/`; filenames sanitised |
| SQL injection | Prevented by SQLAlchemy ORM parameterised queries |
| Dependency scanning | `pip-audit` / Dependabot recommended |

---

## Deployment Options

### Option 1: Docker Compose (Local / Single-Node)

```
┌────────────────────────────────┐
│        docker-compose.yml      │
│  ┌──────┐  ┌───────┐  ┌─────┐ │
│  │ api  │  │postgres│  │redis│ │
│  │:8000 │  │ :5432  │  │:6379│ │
│  └──────┘  └───────┘  └─────┘ │
│       ┌─────────┐             │
│       │  chroma │             │
│       │  :8001  │             │
│       └─────────┘             │
└────────────────────────────────┘
```

See [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) for step-by-step instructions.

### Option 2: Cloud (AWS / GCP / Azure)

```
Internet → ALB/Cloud LB → ECS/Cloud Run (FastAPI)
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
         RDS (PG)        ElastiCache          ChromaDB
                          (Redis)           (self-hosted
                                            or managed)
```

---

## Scalability Considerations

| Dimension | Strategy |
|-----------|----------|
| Horizontal API scaling | Stateless FastAPI containers behind a load balancer |
| Database read load | Read replicas for PostgreSQL; connection pooling via PgBouncer |
| Vector search | ChromaDB supports sharding; or migrate to Pinecone / Weaviate |
| Async document processing | Celery + Redis broker for background OCR and embedding jobs |
| Caching | Redis caches tenant metadata, frequent queries |
| Rate limiting | Per-tenant counters in Redis |

---

## Integration Points

| Integration | Protocol | Notes |
|-------------|----------|-------|
| DeepSeek OCR | HTTPS REST | Text extraction from PDFs / images |
| DeepSeek LLM | HTTPS REST | Answer generation |
| ChromaDB | gRPC / HTTP | Vector storage & similarity search |
| PostgreSQL | TCP (psycopg2) | Primary data store |
| Redis | TCP | Cache, Celery broker |
| External LLMs | HTTPS REST | Swappable via `orchestration_config` |

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Web framework | FastAPI | 0.109+ |
| ORM | SQLAlchemy | 2.0+ |
| Data validation | Pydantic | 2.6+ |
| Database | PostgreSQL | 15 |
| Caching | Redis | 7 |
| Vector store | ChromaDB | 0.4+ |
| Auth | python-jose (JWT) | 3.3+ |
| OCR / LLM | DeepSeek API | — |
| Testing | pytest + httpx | 8.x |
| Container | Docker / Docker Compose | — |
