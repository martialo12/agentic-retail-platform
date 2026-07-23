import pytest

from arp.config import Settings, get_settings


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


def test_get_settings_is_cached():
    assert get_settings() is get_settings()


def test_settings_is_directly_constructible():
    s = Settings(llm_provider="local")
    assert s.llm_provider == "local"
