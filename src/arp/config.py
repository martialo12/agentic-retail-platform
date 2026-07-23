"""Runtime settings, sourced from the environment (see `.env.example`)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["vertex", "gemini", "local", "fake"]


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
    vertex_model: str = "gemini-3.5-flash"
    vertex_embed_model: str = "gemini-embedding-2"

    # Gemini Developer API: same models as Vertex, reached with an API key rather
    # than gcloud ADC. The pragmatic path for a laptop demo.
    gemini_api_key: str = ""
    # An alias rather than a pinned version: which pinned models a key can serve
    # depends on its tier (gemini-2.5-flash now 404s, gemini-3.5-flash 503s on a
    # free key). The alias always resolves to the current stable flash model.
    gemini_model: str = "gemini-flash-latest"
    gemini_embed_model: str = "gemini-embedding-2"

    # Left unset on purpose: embedding width is a property of the configured model,
    # so it is discovered from the first vector rather than guessed here. Pin it only
    # to force a specific (e.g. Matryoshka-truncated) output width.
    embed_dim: int | None = None

    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "llama3.1"

    database_url: str = "postgresql://arp:arp@localhost:5432/arp"
    redis_url: str = "redis://localhost:6379/0"

    # Where the synthetic corpus lives. The default holds for a source checkout;
    # a packaged install (the container) puts `arp` outside the repo tree and
    # therefore sets DATA_DIR explicitly.
    data_dir: Path = Path(__file__).resolve().parents[2] / "data" / "synthetic"


@lru_cache
def get_settings() -> Settings:
    return Settings()
