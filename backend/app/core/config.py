from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    CORS_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"
    AUTH_BYPASS: bool = True
    WORKOS_API_KEY: Optional[str] = None
    WORKOS_CLIENT_ID: Optional[str] = None
    WORKOS_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    STORAGE_PATH: str = "./storage"
    LOG_LEVEL: str = "info"
    CHUNK_TARGET_CHARS: int = 4000
    CHUNK_OVERLAP_CHARS: int = 400

    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"))

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
