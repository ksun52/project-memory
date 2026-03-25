from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    CORS_ORIGINS: str = "http://localhost:3000"
    AUTH_BYPASS: bool = True
    OPENAI_API_KEY: Optional[str] = None
    STORAGE_PATH: str = "./storage"
    LOG_LEVEL: str = "info"
    CHUNK_TARGET_CHARS: int = 4000
    CHUNK_OVERLAP_CHARS: int = 400

    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"))

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
