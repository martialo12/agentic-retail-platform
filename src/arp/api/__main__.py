"""Serve the console API. Run via `make serve-api`."""

import os

import uvicorn

from arp.api.routes import create_app

DEFAULT_PORT = 8000


def main() -> None:
    port = int(os.environ.get("API_PORT") or DEFAULT_PORT)
    uvicorn.run(create_app(), host="0.0.0.0", port=port)  # noqa: S104


if __name__ == "__main__":
    main()
