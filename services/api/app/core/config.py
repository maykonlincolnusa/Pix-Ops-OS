from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "PixOps OS API"
    environment: str = "development"
    debug: bool = True
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pixops"
    redis_url: str = "redis://localhost:6379/0"
    allow_origins: str = "http://localhost:3000"
    jwt_secret_key: str = "change_me_super_secret"
    jwt_algorithm: str = "HS256"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 30
    master_api_key: str = "changeme"
    webhook_allowed_ips: str = ""
    encryption_key: str = "change_me_32_bytes"
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "pixops-os"
    agent_timeout_minutes: int = 20

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allow_origins.split(",") if origin.strip()]

    @property
    def allowed_webhook_ips(self) -> List[str]:
        return [ip.strip() for ip in self.webhook_allowed_ips.split(",") if ip.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
