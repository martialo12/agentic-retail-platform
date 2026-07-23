.PHONY: setup setup-agents lint test up down ingest eval docker tf-validate

# OpenTofu is the default; export TF=terraform to use HashiCorp Terraform instead.
TF ?= tofu
setup:            ; uv sync
setup-agents:     ; uv sync --extra agents
lint:             ; uv run ruff check .
test:             ; uv run pytest -q
up:               ; docker compose up -d
down:             ; docker compose down
ingest:           ; uv run python -m arp.rag.ingest
eval:             ; uv run python -m arp.llmops.eval
docker:           ; docker build -t arp:local .
tf-validate:      ; $(TF) -chdir=infra/terraform init -backend=false -input=false && $(TF) -chdir=infra/terraform validate && $(TF) -chdir=infra/terraform fmt -check -recursive
