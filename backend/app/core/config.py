import os
from typing import Any, Dict, Optional
from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    # Database configuration
    DATABASE_PROVIDER: str = "postgresql"  # 'postgresql' or 'sqlite'
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "document_intelligence"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None
    SYNC_DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str) and v:
            return v
        data = info.data
        provider = data.get("DATABASE_PROVIDER", "postgresql")
        if provider == "sqlite":
            return "sqlite+aiosqlite:///./doc_intel.db"
        
        user = data.get("POSTGRES_USER")
        password = data.get("POSTGRES_PASSWORD")
        host = data.get("POSTGRES_HOST")
        port = data.get("POSTGRES_PORT")
        db = data.get("POSTGRES_DB")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    @field_validator("SYNC_DATABASE_URL", mode="before")
    @classmethod
    def assemble_sync_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str) and v:
            return v
        data = info.data
        provider = data.get("DATABASE_PROVIDER", "postgresql")
        if provider == "sqlite":
            return "sqlite:///./doc_intel.db"
            
        user = data.get("POSTGRES_USER")
        password = data.get("POSTGRES_PASSWORD")
        host = data.get("POSTGRES_HOST")
        port = data.get("POSTGRES_PORT")
        db = data.get("POSTGRES_DB")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    # Redis & Task Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Security
    JWT_SECRET: str = "super-secret-jwt-signing-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    # MinIO / S3 Object Storage
    STORAGE_BACKEND: str = "local"  # 's3' or 'local'
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "documents"
    S3_SECURE: bool = False

    # AI Model Providers
    GEMINI_API_KEY: Optional[str] = None


settings = Settings()
