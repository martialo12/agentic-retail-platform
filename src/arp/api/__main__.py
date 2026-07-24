"""Serve the console API. Run via `make serve-api`."""

import os

import uvicorn

from arp.api.routes import create_app
from arp.observability.logging import configure_logging

DEFAULT_PORT = 8000


def main() -> None:
    configure_logging()
    port = int(os.environ.get("API_PORT") or DEFAULT_PORT)
    # log_config=None: keep our loguru pipeline instead of uvicorn's own dictConfig.
    uvicorn.run(create_app(), host="0.0.0.0", port=port, log_config=None)  # noqa: S104


if __name__ == "__main__":
    main()
