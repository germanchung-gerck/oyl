# API Design

Base URL: `/api/v1`

All requests that modify data require `Content-Type: application/json`.

## Authentication

Include a JWT bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

## Endpoints

### Tenants

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tenants` | Create a tenant |
| GET | `/tenants/{tenant_id}` | Get a tenant |

### Workspaces

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tenants/{tenant_id}/workspaces` | Create a workspace |
| GET | `/workspaces/{workspace_id}` | Get a workspace |

### Teammates

| Method | Path | Description |
|--------|------|-------------|
| POST | `/workspaces/{workspace_id}/teammates` | Create a teammate |
| GET | `/teammates/{teammate_id}` | Get a teammate |

### Assistants

| Method | Path | Description |
|--------|------|-------------|
| POST | `/teammates/{teammate_id}/assistants` | Create an assistant |
| GET | `/assistants/{assistant_id}` | Get an assistant |

### Knowledge

| Method | Path | Description |
|--------|------|-------------|
| POST | `/assistants/{assistant_id}/knowledge/upload` | Upload a document (multipart) |
| POST | `/assistants/{assistant_id}/instruction` | Set system prompt |

### Orchestration

| Method | Path | Description |
|--------|------|-------------|
| POST | `/teammates/{teammate_id}/query` | Send a RAG query |

## Error Responses

| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Resource not found |
| 422 | Unprocessable entity (Pydantic validation) |
| 500 | Internal server error |
