# Database Schema

## Entity-Relationship Overview

```
Tenant (1) ──< Workspace (1) ──< Teammate (1) ──< Assistant (1) ──< KnowledgeBase (1) ──< Document
                                                                  └──< Instruction (1:1)
```

## Tables

### tenants
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR PK | UUID |
| name | VARCHAR(255) | Unique |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

### workspaces
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR PK | UUID |
| tenant_id | VARCHAR FK | → tenants.id |
| name | VARCHAR(255) | |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

### teammates
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR PK | UUID |
| workspace_id | VARCHAR FK | → workspaces.id |
| name | VARCHAR(255) | |
| orchestration_config | JSON | Optional config blob |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

### assistants
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR PK | UUID |
| teammate_id | VARCHAR FK | → teammates.id |
| name | VARCHAR(255) | |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

### knowledge_bases
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR PK | UUID |
| assistant_id | VARCHAR FK | → assistants.id |
| name | VARCHAR(255) | |
| vector_db_id | VARCHAR(255) | ChromaDB collection ID |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

### documents
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR PK | UUID |
| knowledge_base_id | VARCHAR FK | → knowledge_bases.id |
| file_path | VARCHAR(1024) | |
| file_type | VARCHAR(64) | MIME type |
| raw_content | TEXT | Extracted text |
| processed_status | VARCHAR(64) | pending / done / error |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

### instructions
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR PK | UUID |
| assistant_id | VARCHAR FK UNIQUE | → assistants.id |
| system_prompt | TEXT | |
| updated_at | TIMESTAMPTZ | Auto |
