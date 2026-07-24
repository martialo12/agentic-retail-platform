"""Container entrypoint: serve the MCP tool server over HTTP.

Run via `python -m arp.mcp` (what the image's `CMD` does). Transport is
streamable-http rather than stdio because the server is deployed as a network
service; `stateless_http` lets any replica answer any request, which is what
makes horizontal autoscaling on Cloud Run / Kubernetes safe.
"""

import json
import os
from collections.abc import Mapping
from pathlib import Path

from arp.config import get_settings
from arp.mcp.repository import InMemoryRepository
from arp.mcp.server import build_server
from arp.models import CatalogueItem, Order
from arp.observability.logging import configure_logging

DEFAULT_PORT = 8080


def build_repository(
    catalogue_path: Path | None = None,
    orders_path: Path | None = None,
) -> InMemoryRepository:
    """Seed the demo repository from the synthetic corpus (FR: synthetic data only)."""
    data_dir = get_settings().data_dir
    catalogue = Path(catalogue_path or data_dir / "catalogue.json")
    items = [
        CatalogueItem.model_validate(entry)
        for entry in json.loads(catalogue.read_text(encoding="utf-8"))
    ]

    orders_file = Path(orders_path or data_dir / "orders.json")
    orders = (
        [Order.model_validate(entry) for entry in json.loads(orders_file.read_text("utf-8"))]
        if orders_file.exists()
        else []
    )
    return InMemoryRepository(items=items, orders=orders)


def resolve_bind(environ: Mapping[str, str]) -> tuple[str, int]:
    """Cloud Run and Kubernetes both inject the listening port; never hardcode it."""
    return "0.0.0.0", int(environ.get("PORT") or DEFAULT_PORT)  # noqa: S104


def main() -> None:
    configure_logging()
    host, port = resolve_bind(os.environ)
    server = build_server(build_repository(), host=host, port=port, stateless_http=True)
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
