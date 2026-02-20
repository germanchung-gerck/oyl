# oyl# OYL - Multi-Tenant RAG Platform

## Quick Reference

### Architecture
- **Language:** Python
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **Vector DB:** Chroma/FAISS
- **OCR:** DeepSeek-OCR
- **Orchestration:** LangChain

### Project Structure
```
oyl/
├── app/
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── api/             # FastAPI routes
│   ├── services/        # Business logic
│   ├── orchestration/   # Orchestration engine
│   └── rag/             # RAG pipeline
├── docs/                # Architecture & planning
├── docker-compose.yml
└── requirements.txt
```

### Key Issues
- [#2 Architecture Epic](https://github.com/germanchung-gerck/oyl/issues/2)
- [#3 Database Schema](https://github.com/germanchung-gerck/oyl/issues/3)
- [#1 Orchestration Engine](https://github.com/germanchung-gerck/oyl/issues/1)

### Resources
- See `docs/ARCHITECTURE.md` for full system design
- See `docs/DATABASE_SCHEMA.md` for entity relationships
