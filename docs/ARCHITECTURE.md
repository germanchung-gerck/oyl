# Architecture

## Overview

Oyl is a multi-tenant Retrieval-Augmented Generation (RAG) platform built with FastAPI. Each tenant can have multiple workspaces, each workspace hosts teammates (AI agents), and each teammate owns assistants with associated knowledge bases and instructions.

## Component Diagram

```
Client
  │
  ▼
FastAPI App (app/main.py)
  ├── TenantContextMiddleware  – extracts X-Tenant-ID header
  ├── JWT Auth Middleware       – validates Bearer tokens
  │
  └── API Router /api/v1
        ├── /tenants
        ├── /workspaces
        ├── /teammates
        ├── /assistants
        ├── /knowledge
        └── /orchestration
              │
              ▼
         Services Layer
              │
         SQLAlchemy ORM
              │
           PostgreSQL
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.x (mapped columns) |
| Database | PostgreSQL 15 |
| Caching | Redis 7 |
| Vector store | ChromaDB |
| Auth | python-jose (JWT) |
| Testing | pytest + httpx TestClient |
| Container | Docker / Docker Compose |

## Multi-Tenancy Strategy

Tenant isolation is implemented via a Row-Level Security pattern:

1. `X-Tenant-ID` header is read by `TenantContextMiddleware` and stored on `request.state.tenant_id`.
2. Each database row is associated with a `tenant_id` via foreign key cascade.
3. Services validate tenant ownership before returning or mutating data.
