# OYL - Multi-Tenant RAG Platform with DeepSeek-OCR

A modern, scalable platform for building multi-tenant AI assistants with Retrieval-Augmented Generation (RAG), document processing via DeepSeek-OCR, and intelligent orchestration of multiple AI assistants.

## 🎯 Project Overview

OYL enables organizations to:
- **Multi-Tenancy**: Isolate data and configurations for different customers/organizations
- **Workspace Management**: Organize work within tenants
- **Intelligent Teammates**: Create AI agents that orchestrate multiple assistants
- **Knowledge Management**: Upload and process documents with DeepSeek-OCR for RAG
- **Assistant Orchestration**: Route queries intelligently across multiple AI models
- **Scalable Architecture**: Built with FastAPI, PostgreSQL, and vector databases

### Platform Hierarchy
```
Platform
├── Tenant (Organization/Customer)
│   ├── Workspace (Project/Department)
│   │   ├── Teammate (AI Agent)
│   │   │   └── Assistants (1 or more)
│   │   │       ├── Knowledge Base (Documents + Embeddings)
│   │   │       └── Instruction (System Prompt)
│   │   └── Documents (Shared across Teammates)
│   └── Users/Roles
```

## 🏗️ Architecture

- **Backend**: FastAPI (async, modern Python web framework)
- **Database**: PostgreSQL (with Row-Level Security for multi-tenancy)
- **Vector DB**: Chroma/FAISS (for semantic search and RAG)
- **Cache**: Redis (session management, caching)
- **OCR**: DeepSeek-OCR (document text extraction)
- **Task Queue**: Celery (async document processing)
- **Orchestration**: Custom orchestration engine for assistant routing
- **Deployment**: Docker Compose (local), Kubernetes/Cloud-ready

## 🛠️ Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Language** | Python | 3.10+ |
| **Web Framework** | FastAPI | 0.104+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Database** | PostgreSQL | 14+ |
| **Vector DB** | Chroma | Latest |
| **Cache** | Redis | 7+ |
| **OCR** | DeepSeek-OCR | Latest |
| **API Docs** | OpenAPI/Swagger | Auto-generated |

## 📁 Project Structure

```
oyl/
├── app/
│   ├── models/                  # SQLAlchemy database models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── api/v1/endpoints/        # API routes
│   ├── services/                # Business logic
│   ├── middleware/              # Authentication & multi-tenancy
│   ├── main.py                  # FastAPI app
│   ├── config.py                # Configuration
│   └── database.py              # Database connection
├── tests/                       # Test suite
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   └── API_DESIGN.md
├── .env.example                 # Environment template
├── requirements.txt             # Dependencies
├── docker-compose.yml           # Docker services
└── README.md                    # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/germanchung-gerck/oyl.git
   cd oyl
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   # OR
   venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

5. **Start Docker services**
   ```bash
   docker-compose up -d
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

7. **Access the API**
   - **API Docs**: http://localhost:8000/docs
   - **ReDoc**: http://localhost:8000/redoc
   - **API Base URL**: http://localhost:8000/api/v1

## 📚 API Endpoints

### Tenants
- `POST /api/v1/tenants` - Create tenant
- `GET /api/v1/tenants/{tenant_id}` - Get tenant
- `PUT /api/v1/tenants/{tenant_id}` - Update tenant
- `DELETE /api/v1/tenants/{tenant_id}` - Delete tenant

### Workspaces
- `POST /api/v1/tenants/{tenant_id}/workspaces` - Create workspace
- `GET /api/v1/workspaces/{workspace_id}` - Get workspace
- `PUT /api/v1/workspaces/{workspace_id}` - Update workspace
- `DELETE /api/v1/workspaces/{workspace_id}` - Delete workspace

### Teammates
- `POST /api/v1/workspaces/{workspace_id}/teammates` - Create teammate
- `GET /api/v1/teammates/{teammate_id}` - Get teammate
- `POST /api/v1/teammates/{teammate_id}/orchestration` - Configure orchestration
- `POST /api/v1/teammates/{teammate_id}/query` - Query teammate

### Assistants
- `POST /api/v1/teammates/{teammate_id}/assistants` - Create assistant
- `GET /api/v1/assistants/{assistant_id}` - Get assistant
- `POST /api/v1/assistants/{assistant_id}/knowledge/upload` - Upload document
- `POST /api/v1/assistants/{assistant_id}/instruction` - Set instruction
- `POST /api/v1/assistants/{assistant_id}/query` - Query assistant

## 🔧 Configuration

Create a `.env` file with:
```
DATABASE_URL=postgresql://user:password@localhost:5432/oyl
REDIS_URL=redis://localhost:6379
CHROMA_HOST=localhost
CHROMA_PORT=8000
SECRET_KEY=your-secret-key
DEBUG=True
LOG_LEVEL=INFO
```

## 📦 Docker Services

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- **PostgreSQL**: Port 5432
- **Redis**: Port 6379
- **Chroma**: Port 8000

## 🗃️ Database Migrations (Alembic)

This project uses Alembic for SQLAlchemy schema migrations.

```bash
# Initialize Alembic (one time)
alembic init alembic

# Create a migration from model changes
docker compose exec -T api alembic revision --autogenerate -m "describe change"

# Apply migrations
docker compose exec -T api alembic upgrade head

# Show current migration revision
docker compose exec -T api alembic current

# Roll back one revision (if needed)
docker compose exec -T api alembic downgrade -1

# Verify tables in Postgres
docker compose exec -T postgres psql -U oyl_user -d oyl_db -c "\dt"
```

Notes:
- Run Alembic commands in the `api` container so `DATABASE_URL` host `postgres` resolves correctly.
- Initial migration file is in `alembic/versions/`.

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/api/test_tenants.py -v
```

## 📖 Documentation

- **Architecture**: See `docs/ARCHITECTURE.md`
- **Database Schema**: See `docs/DATABASE_SCHEMA.md`
- **API Design**: See `docs/API_DESIGN.md`

## 🔄 Development Workflow

1. Create feature branch: `git checkout -b feat/your-feature`
2. Make changes and test locally
3. Commit: `git commit -m "feat: description (refs #issue)"`
4. Push: `git push origin feat/your-feature`
5. Create Pull Request on GitHub

## 📋 GitHub Issues

Track progress with these issues:
- [#1 - Orchestration Engine](https://github.com/germanchung-gerck/oyl/issues/1)
- [#2 - Architecture Epic](https://github.com/germanchung-gerck/oyl/issues/2)
- [#3 - Database Schema](https://github.com/germanchung-gerck/oyl/issues/3)
- [#4 - RAG Pipeline](https://github.com/germanchung-gerck/oyl/issues/4)
- [#5 - API Endpoints](https://github.com/germanchung-gerck/oyl/issues/5)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License

## 🆘 Troubleshooting

- **Port 8000 in use**: `uvicorn app.main:app --reload --port 8001`
- **PostgreSQL connection failed**: Run `docker-compose up -d`
- **Module not found**: Run `pip install -r requirements.txt`

## 📞 Support

Create a GitHub Issue for questions or problems.

---

**Ready to build amazing AI assistants! 🚀**
