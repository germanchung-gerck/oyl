from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Oyl RAG Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://oyl_user:oyl_pass@localhost:5432/oyl_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Vector DB (Chroma)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OCR_MODEL: str = "deepseek-ocr:latest"
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"
    TAGGING_MODEL: str = "neural-chat:7b"
    REASONING_MODEL: str = "deepseek-r1:8b"
    FAST_MODEL: str = "qwen3:7b"

    # RAG Pipeline
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_CHUNKS: int = 5
    TAGS_PER_CHUNK: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
