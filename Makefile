.PHONY: setup setup-agents lint test up down ingest eval docker tf-validate k8s-validate iac

# OpenTofu is the default; export TF=terraform to use HashiCorp Terraform instead.
TF ?= tofu
K8S_VERSION ?= 1.30.0

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
docker:           ; docker build -t arp:local .
tf-validate:      ; $(TF) -chdir=infra/terraform init -backend=false -input=false && $(TF) -chdir=infra/terraform validate && $(TF) -chdir=infra/terraform fmt -check -recursive
# Schema-validates against upstream OpenAPI, so no cluster is needed.
k8s-validate:     ; docker run --rm -v "$(CURDIR)/infra/k8s:/work:ro" ghcr.io/yannh/kubeconform:latest -strict -summary -kubernetes-version $(K8S_VERSION) /work
iac: docker tf-validate k8s-validate
