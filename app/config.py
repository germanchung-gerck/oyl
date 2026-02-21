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

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_OCR_MODEL: str = "deepseek-r1:7b"
    OLLAMA_TAGGING_MODEL: str = "neural-chat:7b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_REASONING_MODEL: str = "deepseek-r1:7b"
    OLLAMA_FAST_MODEL: str = "qwen2.5:7b"
    OLLAMA_TIMEOUT: int = 120

    # RAG
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_RETRIEVED_CHUNKS: int = 5

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
