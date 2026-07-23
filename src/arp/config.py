"""Runtime settings, sourced from the environment (see `.env.example`)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["vertex", "local", "fake"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    llm_provider: Provider = "vertex"

    vertex_project: str = ""
    vertex_location: str = "europe-west1"
    vertex_model: str = "gemini-1.5-pro"
    vertex_embed_model: str = "text-embedding-004"

    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "llama3.1"

    database_url: str = "postgresql://arp:arp@localhost:5432/arp"
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
