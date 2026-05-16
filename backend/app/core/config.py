"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    jwt_secret: str = Field(default="atlaslens-dev-secret-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expires_minutes: int = Field(default=60 * 24)


@lru_cache
def get_settings() -> Settings:
    return Settings()
