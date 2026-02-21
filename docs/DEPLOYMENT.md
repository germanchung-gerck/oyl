# Deployment Guide

## Table of Contents

1. [Local Development Setup](#1-local-development-setup)
2. [Docker & Docker Compose](#2-docker--docker-compose)
3. [Environment Variables](#3-environment-variables)
4. [Database Initialisation](#4-database-initialisation)
5. [Cloud Deployment Options](#5-cloud-deployment-options)
6. [Scalability Considerations](#6-scalability-considerations)
7. [Monitoring & Logging](#7-monitoring--logging)
8. [Backup & Recovery](#8-backup--recovery)

---

## 1. Local Development Setup

### Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| Python | 3.10 | [python.org](https://www.python.org/downloads/) |
| Docker | 24 | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | 2.x | Bundled with Docker Desktop |
| Git | 2.x | [git-scm.com](https://git-scm.com/) |

### Step-by-step

```bash
# 1. Clone the repository
git clone https://github.com/germanchung-gerck/oyl.git
cd oyl

# 2. Create and activate a Python virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# OR
venv\Scripts\activate           # Windows PowerShell

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy the example environment file and edit it
cp .env.example .env
# Open .env and update any values as needed (see Section 3)

# 5. Start backing services (PostgreSQL, Redis, ChromaDB)
docker compose up -d postgres redis chroma

# 6. Apply database schema
#    (Alembic migrations – once configured)
#    alembic upgrade head
#
#    OR create tables directly via SQLAlchemy for development:
python - <<'EOF'
from app.database import engine
from app.models.base import Base
import app.models  # ensure all models are registered
Base.metadata.create_all(bind=engine)
print("Tables created.")
EOF

# 7. Start the FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access points**:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/api/v1` | API base |

### Running tests locally

```bash
# Run all tests (uses SQLite in-memory, no Docker needed)
pytest

# Run with coverage report
pytest --cov=app tests/

# Run a specific test file verbosely
pytest tests/api/test_tenants.py -v
```

---

## 2. Docker & Docker Compose

### Services defined in `docker-compose.yml`

```
┌────────────────────────────────────────────┐
│              docker-compose.yml             │
│                                            │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  │
│  │   api   │  │ postgres │  │  redis   │  │
│  │  :8000  │  │  :5432   │  │  :6379   │  │
│  └─────────┘  └──────────┘  └──────────┘  │
│                                            │
│            ┌──────────┐                    │
│            │  chroma  │                    │
│            │  :8001   │  (host port)        │
│            └──────────┘                    │
└────────────────────────────────────────────┘
```

| Service | Image | Host port | Purpose |
|---------|-------|-----------|---------|
| `api` | Built from `Dockerfile` | `8000` | FastAPI application |
| `postgres` | `postgres:15-alpine` | `5432` | Primary database |
| `redis` | `redis:7-alpine` | `6379` | Cache / broker |
| `chroma` | `chromadb/chroma:latest` | `8001` | Vector store |

### Common commands

```bash
# Start all services in the background
docker compose up -d

# Start only backing services (run the app locally)
docker compose up -d postgres redis chroma

# View live logs from all services
docker compose logs -f

# View logs from a specific service
docker compose logs -f api

# Rebuild the API image after code changes
docker compose build api

# Stop all services (data persisted in volumes)
docker compose down

# Stop and remove volumes (resets all data)
docker compose down -v

# Scale the API horizontally (requires a load balancer)
docker compose up -d --scale api=3
```

### Dockerfile

The `Dockerfile` builds a minimal production image:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

For production, consider adding:
- A non-root user (`USER appuser`)
- `--workers 4` (Gunicorn with Uvicorn workers)
- Health-check instruction (`HEALTHCHECK`)

---

## 3. Environment Variables

Copy `.env.example` to `.env` and update these values:

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APP_NAME` | `Oyl RAG Platform` | No | Application display name |
| `APP_VERSION` | `0.1.0` | No | Semantic version |
| `DEBUG` | `false` | No | Enable debug mode (never `true` in production) |
| `DATABASE_URL` | `postgresql://oyl_user:oyl_pass@postgres:5432/oyl_db` | **Yes** | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | **Yes** | Redis connection string |
| `CHROMA_HOST` | `chroma` | **Yes** | ChromaDB hostname |
| `CHROMA_PORT` | `8000` | **Yes** | ChromaDB port (internal) |
| `SECRET_KEY` | `change-me-in-production-…` | **Yes** | JWT signing secret (use a long random string) |
| `ALGORITHM` | `HS256` | No | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | No | JWT token lifetime |

### Generating a secure `SECRET_KEY`

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Environment-specific `.env` files

```
.env             # local development (gitignored)
.env.example     # template committed to the repo
.env.test        # overrides for test runs
.env.production  # managed by secret manager / CI
```

---

## 4. Database Initialisation

### Using Alembic (recommended)

```bash
# Initialise Alembic (first time only)
alembic init alembic

# Edit alembic/env.py to import your models and use DATABASE_URL
# Then generate the initial migration
alembic revision --autogenerate -m "initial schema"

# Apply migrations
alembic upgrade head

# Check current migration state
alembic current

# Generate a new migration after model changes
alembic revision --autogenerate -m "add indexes"
```

### Using SQLAlchemy directly (development only)

```python
from app.database import engine
from app.models.base import Base
import app.models  # registers all models

Base.metadata.create_all(bind=engine)
```

### Seed data (optional)

```bash
python - <<'EOF'
from app.database import SessionLocal
from app.services.tenant_service import create_tenant
from app.schemas.tenant import TenantCreate

db = SessionLocal()
create_tenant(db, TenantCreate(name="Demo Tenant"))
db.close()
print("Seed data inserted.")
EOF
```

---

## 5. Cloud Deployment Options

### AWS (ECS Fargate + RDS + ElastiCache)

```
Internet
  │
  ▼
Application Load Balancer (ALB)
  │
  ▼
ECS Fargate (FastAPI containers)
  │         │              │
  ▼         ▼              ▼
RDS       ElastiCache   ECS/EC2
(PG 15)   (Redis 7)    (ChromaDB)
```

**Steps**:
1. Push Docker image to Amazon ECR
2. Create an ECS task definition using the image
3. Create an ECS Fargate service behind an ALB
4. Provision RDS PostgreSQL and ElastiCache Redis
5. Store secrets in AWS Secrets Manager; inject via ECS task environment
6. Set `DATABASE_URL`, `REDIS_URL`, and `SECRET_KEY` from Secrets Manager

**Minimal `ecs-task-definition.json` snippet**:
```json
{
  "containerDefinitions": [{
    "name": "oyl-api",
    "image": "<account>.dkr.ecr.<region>.amazonaws.com/oyl:latest",
    "portMappings": [{ "containerPort": 8000 }],
    "environment": [
      { "name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:..." }
    ]
  }]
}
```

---

### GCP (Cloud Run + Cloud SQL + Memorystore)

```
Internet → Cloud Load Balancing → Cloud Run (FastAPI)
                                        │
                              ┌─────────┼─────────┐
                              ▼         ▼         ▼
                          Cloud SQL  Memorystore  GCE/GKE
                          (PG 15)   (Redis 7)   (ChromaDB)
```

**Steps**:
1. Build and push image to Google Artifact Registry
2. Deploy to Cloud Run: `gcloud run deploy oyl-api --image ...`
3. Connect to Cloud SQL using Cloud SQL Auth Proxy
4. Store secrets in Google Secret Manager

---

### Azure (Container Apps + Azure Database + Azure Cache)

```
Internet → Azure Front Door → Container Apps (FastAPI)
                                     │
                           ┌─────────┼──────────┐
                           ▼         ▼           ▼
                       Azure DB   Azure Cache  ACI/AKS
                       (PG flex)  (Redis)    (ChromaDB)
```

---

### Render.com (beginner-friendly)

1. Connect your GitHub repository to Render
2. Create a **Web Service** (Docker runtime), port `8000`
3. Add a **PostgreSQL** managed database and copy `DATABASE_URL` to environment variables
4. Add a **Redis** instance and copy `REDIS_URL`
5. Deploy — Render builds and runs the Docker container automatically

---

### Railway.app (beginner-friendly)

1. Create a new project from your GitHub repository
2. Add PostgreSQL and Redis plugins
3. Set environment variables in the Railway dashboard
4. Railway auto-builds and deploys on every `git push`

---

## 6. Scalability Considerations

| Concern | Strategy |
|---------|----------|
| **API horizontal scaling** | Run multiple stateless FastAPI containers behind a load balancer. Session state lives in Redis, not in-process. |
| **Database connection pooling** | Use PgBouncer or SQLAlchemy's built-in pool (`pool_size`, `max_overflow`). |
| **Read replicas** | Route read-heavy queries to PostgreSQL read replicas. |
| **Async document processing** | Move OCR and embedding jobs to Celery workers with a Redis broker to avoid blocking the API. |
| **Vector store scaling** | ChromaDB supports multiple replicas. For very large corpora, consider managed solutions (Pinecone, Weaviate, Qdrant). |
| **CDN / caching** | Cache static API responses (e.g., tenant metadata) in Redis with a TTL. |
| **Rate limiting** | Enforce per-tenant request limits using Redis sliding-window counters. |

### Example `docker compose` scale (development)

```bash
docker compose up -d --scale api=3
# Add an nginx/Traefik load balancer in front for production
```

---

## 7. Monitoring & Logging

### Structured logging

FastAPI and Uvicorn output structured logs to `stdout`. In Docker, these are captured by the container runtime and can be forwarded to any log aggregator.

```bash
# View logs in Docker Compose
docker compose logs -f api

# JSON log format (recommended for production)
uvicorn app.main:app --log-config log_config.json
```

### Health check

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

Use this endpoint with Docker / Kubernetes liveness and readiness probes:

```yaml
# Kubernetes example
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Recommended monitoring stack

| Tool | Purpose |
|------|---------|
| Prometheus + Grafana | Metrics (request rate, latency, error rate) |
| Loki | Log aggregation |
| Sentry | Error tracking and alerting |
| Datadog / New Relic | Full APM (alternative) |

### Adding Prometheus metrics (example)

```bash
pip install prometheus-fastapi-instrumentator
```

```python
# app/main.py
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

---

## 8. Backup & Recovery

### PostgreSQL backups

#### Continuous WAL archiving (production)

Enable WAL archiving and use `pgBackRest` or `Barman` for point-in-time recovery.

#### Ad-hoc dump

```bash
# Dump the entire database
pg_dump -h localhost -U oyl_user -d oyl_db -F c -f oyl_backup_$(date +%Y%m%d).dump

# Restore from dump
pg_restore -h localhost -U oyl_user -d oyl_db oyl_backup_20240115.dump
```

#### Docker Compose backup script

```bash
docker compose exec postgres \
  pg_dump -U oyl_user oyl_db \
  > backups/oyl_$(date +%Y%m%d_%H%M%S).sql
```

### Redis backups

Redis is used for ephemeral data (sessions, rate-limit counters). Enable RDB snapshots in `redis.conf`:

```
save 900 1
save 300 10
save 60 10000
dir /data
dbfilename dump.rdb
```

### ChromaDB backups

ChromaDB persists data in the `chroma_data` Docker volume. Back up the volume contents:

```bash
docker run --rm \
  -v oyl_chroma_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/chroma_$(date +%Y%m%d).tar.gz /data
```

### Recovery Procedure

1. Restore PostgreSQL from latest dump: `pg_restore …`
2. Replay WAL logs to desired point-in-time
3. Restore ChromaDB volume from tarball
4. Restart all services: `docker compose up -d`
5. Verify health: `curl http://localhost:8000/health`
6. Run smoke tests: `pytest tests/api/test_tenants.py -v`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Connection refused` to PostgreSQL | Run `docker compose up -d postgres` |
| `Module not found` | Activate venv and run `pip install -r requirements.txt` |
| Port `8000` already in use | Use `--port 8001` or stop the conflicting process |
| JWT validation error | Check `SECRET_KEY` matches between token issuer and API |
| `422 Unprocessable Entity` | Check request body matches the Pydantic schema |
| ChromaDB collection not found | Ensure `chroma` service is running; verify `CHROMA_HOST`/`CHROMA_PORT` |
