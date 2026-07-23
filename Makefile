.PHONY: setup setup-agents lint test up down ingest eval ask enrich serve serve-docker docker tf-validate k8s-validate iac

# OpenTofu is the default; export TF=terraform to use HashiCorp Terraform instead.
TF ?= tofu
K8S_VERSION ?= 1.30.0
PORT ?= 8080

# src-layout, stated once. pytest already declares it via `pythonpath`; the
# module entrypoints need the same, so they no longer depend on the editable
# install being healthy — on macOS/iCloud its .pth gets flagged hidden, and
# CPython silently skips hidden .pth files.
RUN := PYTHONPATH=src uv run
setup:            ; uv sync
setup-agents:     ; uv sync --extra agents
lint:             ; uv run ruff check .
test:             ; uv run pytest -q
up:               ; docker compose up -d
down:             ; docker compose down
ingest:           ; $(RUN) python -m arp.rag.ingest
eval:             ; $(RUN) python -m arp.llmops.eval
serve:            ; $(RUN) python -m arp.mcp
# make ask Q="Où en est ma commande o002 ?"   /   make enrich ID=p003
ask:              ; $(RUN) python -m arp.cli ask "$(Q)"
enrich:           ; $(RUN) python -m arp.cli enrich "$(ID)"
docker:           ; docker build -t arp:local .
# Same entrypoint, but through the image that ships to Cloud Run / GKE.
serve-docker: docker
	docker run --rm -p $(PORT):8080 --env-file .env -e DATA_DIR=/app/data/synthetic arp:local
tf-validate:      ; $(TF) -chdir=infra/terraform init -backend=false -input=false && $(TF) -chdir=infra/terraform validate && $(TF) -chdir=infra/terraform fmt -check -recursive
# Schema-validates against upstream OpenAPI, so no cluster is needed.
k8s-validate:     ; docker run --rm -v "$(CURDIR)/infra/k8s:/work:ro" ghcr.io/yannh/kubeconform:latest -strict -summary -kubernetes-version $(K8S_VERSION) /work
iac: docker tf-validate k8s-validate
