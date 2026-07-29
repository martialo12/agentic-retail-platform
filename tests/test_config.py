from pathlib import Path

import pytest

from arp.config import Settings, get_settings, redact_dsn


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_to_vertex_provider(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert get_settings().llm_provider == "vertex"


def test_reads_provider_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "local")
    assert get_settings().llm_provider == "local"


def test_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(ValueError):
        get_settings()


def test_env_var_names_are_case_insensitive(monkeypatch):
    monkeypatch.setenv("database_url", "postgresql://x:y@host:5432/db")
    assert get_settings().database_url == "postgresql://x:y@host:5432/db"


def test_datastore_and_model_defaults(monkeypatch):
    for var in ("DATABASE_URL", "REDIS_URL", "VERTEX_LOCATION", "VERTEX_MODEL"):
        monkeypatch.delenv(var, raising=False)
    s = get_settings()
    assert s.database_url.startswith("postgresql://")
    assert s.redis_url.startswith("redis://")
    assert s.vertex_location == "europe-west1"
    assert s.vertex_model == "gemini-3.5-flash"


def test_embedding_model_default_is_current(monkeypatch):
    monkeypatch.delenv("VERTEX_EMBED_MODEL", raising=False)
    assert get_settings().vertex_embed_model == "gemini-embedding-2"


def test_embed_dim_is_unset_by_default(monkeypatch):
    """Unset means 'discover the width from the model' rather than guess it."""
    monkeypatch.delenv("EMBED_DIM", raising=False)
    assert get_settings().embed_dim is None


def test_embed_dim_can_be_pinned(monkeypatch):
    monkeypatch.setenv("EMBED_DIM", "1536")
    assert get_settings().embed_dim == 1536


def test_data_dir_defaults_to_the_repo_corpus(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    data_dir = get_settings().data_dir
    assert (data_dir / "catalogue.json").exists()


def test_data_dir_is_overridable(monkeypatch):
    """The packaged image installs `arp` outside the repo tree, so the corpus moves."""
    monkeypatch.setenv("DATA_DIR", "/app/data/synthetic")
    assert get_settings().data_dir == Path("/app/data/synthetic")


def test_cors_defaults_to_the_local_console(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert get_settings().cors_origins == [
        "http://localhost:5173",
        "http://localhost:4173",
    ]


def test_cors_accepts_a_comma_separated_list(monkeypatch):
    """Terraform injects a plain env var, not JSON."""
    monkeypatch.setenv("CORS_ORIGINS", "https://console.run.app, https://other.app")
    assert get_settings().cors_origins == [
        "https://console.run.app",
        "https://other.app",
    ]


def test_cors_still_accepts_json(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://console.run.app"]')
    assert get_settings().cors_origins == ["https://console.run.app"]


def test_cors_empty_env_allows_no_origin(monkeypatch):
    """An empty list is the safe reading: deny, never fall back to a wildcard."""
    monkeypatch.setenv("CORS_ORIGINS", "")
    assert get_settings().cors_origins == []


def test_get_settings_is_cached():
    assert get_settings() is get_settings()


def test_settings_is_directly_constructible():
    s = Settings(llm_provider="local")
    assert s.llm_provider == "local"


def test_redact_dsn_masks_the_password():
    """A DSN printed once is a credential kept forever in Cloud Logging."""
    masked = redact_dsn("postgresql://arp:72ruihIBjdZUsAQ1xV2V6TQS@172.28.0.3:5432/arp")
    assert masked == "postgresql://arp:***@172.28.0.3:5432/arp"
    assert "72ruih" not in masked


def test_redact_dsn_leaves_a_passwordless_dsn_alone():
    dsn = "postgresql://arp@localhost:5432/arp"
    assert redact_dsn(dsn) == dsn


def test_redact_dsn_handles_a_password_with_url_characters():
    masked = redact_dsn("postgresql://arp:p%40ss%2Fword@host:5432/arp")
    assert "p%40ss" not in masked
    assert masked.startswith("postgresql://arp:***@host:5432")
