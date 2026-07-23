"""The container entrypoint: what `CMD` runs inside the image."""

import json

import pytest

from arp.mcp.__main__ import build_repository, resolve_bind
from arp.mcp.server import build_server


def test_build_repository_seeds_the_synthetic_catalogue():
    repo = build_repository()
    assert repo.get_product("p001") is not None
    assert len(repo.list_products()) == 20


def test_build_repository_tolerates_a_missing_orders_file(tmp_path):
    catalogue = tmp_path / "catalogue.json"
    catalogue.write_text(
        json.dumps([{"id": "p1", "title": "Chaise", "specs": {}, "category": "mobilier"}]),
        encoding="utf-8",
    )
    repo = build_repository(catalogue_path=catalogue, orders_path=tmp_path / "absent.json")
    assert repo.get_product("p1") is not None
    assert repo.get_order("o1") is None


def test_build_repository_seeds_orders_when_the_file_exists(tmp_path):
    catalogue = tmp_path / "catalogue.json"
    catalogue.write_text(json.dumps([]), encoding="utf-8")
    orders = tmp_path / "orders.json"
    orders.write_text(
        json.dumps([{"id": "o1", "status": "expédiée", "product_ids": ["p1"]}]),
        encoding="utf-8",
    )
    repo = build_repository(catalogue_path=catalogue, orders_path=orders)
    assert repo.get_order("o1").status == "expédiée"


def test_resolve_bind_defaults_to_all_interfaces_on_8080():
    assert resolve_bind({}) == ("0.0.0.0", 8080)


def test_resolve_bind_honours_the_platform_injected_port(monkeypatch):
    """Cloud Run injects $PORT; the container must listen on it, not a hardcoded one."""
    assert resolve_bind({"PORT": "9090"}) == ("0.0.0.0", 9090)


def test_resolve_bind_rejects_a_non_numeric_port():
    with pytest.raises(ValueError):
        resolve_bind({"PORT": "not-a-port"})


def test_build_server_accepts_transport_settings():
    server = build_server(build_repository(), host="0.0.0.0", port=8080, stateless_http=True)
    assert server.settings.host == "0.0.0.0"
    assert server.settings.port == 8080
    assert server.settings.stateless_http is True
