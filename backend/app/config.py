"""
Application configuration via Pydantic BaseSettings.
All values are loaded from environment variables / .env file.
"""
from functools import lru_cache
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),  # allow fields starting with model_
    )


    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "NetSec Compliance Auditor"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    secret_key: str = "CHANGE_ME"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "netsec"
    postgres_password: str = "password"
    postgres_db: str = "netsec_auditor"

    @computed_field  # type: ignore[misc]
    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── MongoDB ───────────────────────────────────────────────────────────────
    mongo_host: str = "mongo"
    mongo_port: int = 27017
    mongo_user: str = "netsec"
    mongo_password: str = "password"
    mongo_db: str = "netsec_auditor"

    @computed_field  # type: ignore[misc]
    @property
    def mongo_url(self) -> str:
        return (
            f"mongodb://{self.mongo_user}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}"
        )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── AI / HuggingFace ─────────────────────────────────────────────────────
    hf_model_name: str = "facebook/bart-large-mnli"
    model_cache_dir: str = "/root/.cache/huggingface"

    # ── File Upload ───────────────────────────────────────────────────────────
    max_upload_size_mb: int = 50
    upload_dir: str = "/tmp/uploads"

    @computed_field  # type: ignore[misc]
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    return Settings()
