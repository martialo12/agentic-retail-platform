"""Test-wide isolation from the developer's machine.

The suite must give the same answer on a laptop with a live `.env` and in CI
with none. Without this, whatever a developer happens to have configured —
a provider, an embedding width — leaks into assertions about defaults.
"""

import pytest

from arp.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _ignore_dotenv(monkeypatch):
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
