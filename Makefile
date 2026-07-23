.PHONY: setup setup-agents lint test up down ingest eval
setup:            ; uv sync
setup-agents:     ; uv sync --extra agents
lint:             ; uv run ruff check .
test:             ; uv run pytest -q
up:               ; docker compose up -d
down:             ; docker compose down
ingest:           ; uv run python -m arp.rag.ingest
eval:             ; uv run python -m arp.llmops.eval
