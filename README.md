# Oyl – Multi-Tenant RAG Platform

A production-ready FastAPI scaffolding for a multi-tenant Retrieval-Augmented Generation (RAG) platform.

## Quick Start

### Prerequisites
- Docker & Docker Compose

### Run with Docker Compose

```bash
cp .env.example .env
docker-compose up --build
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### Run Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL etc.
python main.py
```

## Project Structure

```
oyl/
├── app/
│   ├── main.py          # FastAPI app
│   ├── config.py        # Settings (pydantic-settings)
│   ├── database.py      # SQLAlchemy session
│   ├── models/          # ORM models
│   ├── schemas/         # Pydantic schemas
│   ├── api/v1/          # Route handlers
│   ├── services/        # Business logic
│   ├── middleware/       # Auth + tenant context
│   └── utils/           # Shared utilities
├── tests/               # Pytest suite
├── docs/                # Architecture, DB schema, API design
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [API Design](docs/API_DESIGN.md)