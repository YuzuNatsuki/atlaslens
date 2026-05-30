"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "atlaslens-dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_key: str = Field(default="")
    azure_openai_api_version: str = Field(default="2024-10-21")
    azure_openai_chat_deployment: str = Field(default="gpt-4o")
    azure_openai_chat_deployment_fast: str = Field(default="gpt-4o-mini")
    azure_openai_embedding_deployment: str = Field(default="text-embedding-3-large")

    azure_ai_foundry_project_endpoint: str = Field(default="")

    azure_search_endpoint: str = Field(default="")
    azure_search_api_key: str = Field(default="")
    azure_search_index_name: str = Field(default="atlaslens-knowledge")

    cosmos_endpoint: str = Field(default="")
    cosmos_key: str = Field(default="")
    cosmos_database: str = Field(default="atlaslens")
    cosmos_container: str = Field(default="knowledge")

    app_env: str = Field(default="local")
    data_dir: Path = Field(default=Path("./data/atlascorp"))
    log_level: str = Field(default="INFO")

    # JWT secret. Override via env in production.
    jwt_secret: str = Field(default=_DEV_JWT_SECRET)
    jwt_algorithm: str = Field(default="HS256")
    jwt_expires_minutes: int = Field(default=60 * 24)

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if self.app_env == "production":
            if self.jwt_secret == _DEV_JWT_SECRET:
                raise ValueError("JWT_SECRET must be set in production")
            if len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
