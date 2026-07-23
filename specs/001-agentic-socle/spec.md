# Feature Specification: Agentic Retail Socle + Two Demo Agents

**Feature Branch**: `001-agentic-socle`

**Created**: 2026-07-23

**Status**: Draft

**Input**: Design doc `docs/design/2026-07-23-agentic-retail-platform-design.md` — build a reusable agentic socle (registry, MCP tools, identity/policy, LangGraph orchestration, RAG, LLMOps, GCP-ready IaC) proven by two agents plugged into it, runnable locally.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enrich an incomplete product sheet (Priority: P1)

A catalogue manager submits a raw, incomplete product sheet (title + partial specs). The `product-enricher` agent retrieves similar catalogue entries, drafts structured enriched attributes (category, materials, use-cases, SEO description) with a confidence score, self-checks them, and either emits validated attributes or escalates to a human when confidence is low.

**Why this priority**: It is the flagship retail use-case and the clearest proof that the socle turns a vague brief into structured, auditable output. It alone is a viable MVP.

**Independent Test**: Feed one incomplete sheet through the enricher against the synthetic catalogue; assert a schema-valid `EnrichedProduct` is produced (high confidence) or an escalation is raised (low confidence), and that a JSONL trace was written.

**Acceptance Scenarios**:

1. **Given** an incomplete sheet with a clear category signal, **When** the enricher runs, **Then** it emits a schema-valid `EnrichedProduct` with `confidence >= threshold` and calls `write_enrichment` (policy-permitted).
2. **Given** a sheet with ambiguous signals, **When** the enricher runs, **Then** it routes to escalation and does NOT call `write_enrichment`.
3. **Given** any run, **When** it completes, **Then** exactly one timestamped JSONL record with the run's events exists under `logs/runs/`.

---

### User Story 2 - Answer a customer question via tools on the same socle (Priority: P2)

A customer asks an order/product question. The `customer-assistant` agent, declared in the same registry and running on the same orchestration/policy/MCP stack, uses tools (`lookup_order`, `get_product`, `search_catalog`) to answer, escalating on sensitive intents. It is NOT granted `write_enrichment`.

**Why this priority**: It proves the socle is reusable — a new agent is a new spec + nodes, not a new platform — which is the core selling point.

**Independent Test**: Ask an order-status question; assert `lookup_order` is invoked through MCP under policy; then assert an attempt by this agent to call `write_enrichment` is refused by policy and traced.

**Acceptance Scenarios**:

1. **Given** an order-status question, **When** the assistant runs, **Then** it calls `lookup_order` via MCP and returns a schema-valid `AssistantReply`.
2. **Given** the assistant's spec (no `write_enrichment`), **When** it attempts `write_enrichment`, **Then** the policy layer raises and the refusal is traced; no write occurs.

---

### User Story 3 - Register a new agent by configuration (Priority: P3)

A developer adds a new agent by writing a registry YAML spec (id, model, allowed tools, escalation policy, owner) and a prompt; no socle code changes.

**Why this priority**: Demonstrates the "poser les fondations, pas du legacy" thesis — extension by configuration.

**Independent Test**: Add a minimal third spec granting a subset of tools; assert `load_agent` returns a valid `AgentSpec` and that the policy layer authorizes exactly the granted tools.

**Acceptance Scenarios**:

1. **Given** a new valid spec YAML, **When** `load_agent` runs, **Then** a validated `AgentSpec` is returned.
2. **Given** a spec referencing an unknown tool, **When** `load_agent` runs, **Then** a validation error is raised.

### User Story 4 - Show the socle to a non-technical stakeholder (Priority: P2)

A client watches a browser, not a terminal. They ask the assistant a routine question and
see which MCP tools answered it; they then ask for a refund and see the run stop, refused
and traced, before any model call is made.

**Why this priority**: The socle's value is governance — authorization, escalation, auditability.
A terminal makes that legible to engineers only. This story is what turns the guarantees into
something a buyer can judge.

**Independent Test**: Drive the web UI with the fake provider; assert that a sensitive-intent
question renders an escalation with its reason, and that the run appears in the observability
view with its full event timeline.

**Acceptance Scenarios**:

1. **Given** a routine order question, **When** it is submitted from the UI, **Then** the run's events stream in as they occur and the tools used are displayed.
2. **Given** a question containing a sensitive intent, **When** it is submitted, **Then** the UI shows the escalation and its reason, and no answer is presented as authoritative.
3. **Given** a completed run, **When** the observability view is opened, **Then** that run is listed and its event timeline is inspectable.

### Edge Cases

- LLM returns output that fails schema validation → bounded retry (max N), then escalate; never emit unvalidated output.
- The UI client disconnects mid-run → the run is cancelled; no orphaned work continues server-side.
- The run store is unreachable → the run still completes and its JSONL audit record is still written; only the observability view degrades.
- Requested provider (Vertex) is unconfigured at runtime → fall back to the configured local provider; surface which provider served the run in the trace.
- Retrieval returns zero hits → enricher drafts from the sheet alone and lowers confidence (more likely to escalate).
- A tool call targets a tool not in the agent's `allowed_tools` → refuse and trace; the call never executes.
- pgvector/database unreachable → integration-level features fail loudly; unit tests remain green via injected fakes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load an agent from a YAML registry spec into a validated `AgentSpec` (id, model, allowed_tools, escalation policy, owner, prompt path).
- **FR-002**: System MUST reject a spec that omits a required field or references a tool absent from the tool catalogue.
- **FR-003**: System MUST expose business tools (`search_catalog`, `get_product`, `write_enrichment`, `lookup_order`) over an MCP server; agents MUST reach tools only through MCP.
- **FR-004**: System MUST authorize every tool call against the calling agent's `allowed_tools` and refuse (with a traced event) any call outside that set.
- **FR-005**: System MUST orchestrate agents as a LangGraph state machine with a human-in-the-loop escalation path.
- **FR-006**: System MUST retrieve context from a pgvector store using an interface that is AlloyDB-compatible in production.
- **FR-007**: System MUST route all model calls through one provider-agnostic `LLMProvider` interface; default target Vertex AI Gemini, with a configurable local fallback, and a deterministic fake for tests.
- **FR-008**: System MUST validate every LLM result against a Pydantic schema; on parse failure it MUST retry up to a bounded limit, then escalate.
- **FR-009**: System MUST write exactly one timestamped JSONL record per run, capturing retrieval, tool-call, llm-call, escalation, and output events.
- **FR-010**: System MUST provide `product-enricher` producing a validated `EnrichedProduct` (category, materials, use_cases, seo_description, confidence).
- **FR-011**: System MUST provide `customer-assistant` producing a validated `AssistantReply`, granted `lookup_order,get_product,search_catalog` but NOT `write_enrichment`.
- **FR-012**: System MUST run an evaluation harness over a synthetic golden set, reporting field-coverage, exact-match vs reference, and escalation-rate.
- **FR-013**: System MUST use only synthetic catalogue data; no real customer data is ingested or stored.
- **FR-014**: System MUST provide GCP-ready IaC (Dockerfile, Terraform for Cloud Run/AlloyDB/GCS/Memorystore, K8s manifests) that passes `validate` without being deployed.
- **FR-015**: System MUST expose both agents over an HTTP API that streams each run's events (retrieval, tool-call, llm-call, escalation, output) as they occur, rather than only on completion.
- **FR-016**: System MUST persist every run to a queryable, AlloyDB-compatible store, without replacing the JSONL record — the file remains the audit artefact, the store is a read index.
- **FR-017**: System MUST provide a web interface covering both agents and run observability, in which an escalation is presented as a first-class outcome and never as an error.
- **FR-018**: The HTTP API is unauthenticated in this POC. Its IaC MUST therefore declare it non-public by construction — internal ingress and an empty invoker set, as the MCP service already does — so that a deployment cannot accidentally expose it. Authentication is a prerequisite for granting any invoker.

### Key Entities

- **AgentSpec**: A registered agent — id, model, allowed_tools, escalation policy, owner, prompt path.
- **Tool**: A business capability exposed over MCP; referenced by name in `allowed_tools`.
- **EnrichedProduct**: Structured enricher output — category, materials, use_cases, seo_description, confidence.
- **AssistantReply**: Structured assistant output — answer, tool_calls_used, escalate flag.
- **RunTrace**: One JSONL record per run — agent id, timestamp, ordered events, serving provider, outcome.
- **CatalogueItem**: A synthetic product — id, title, partial specs, category; corpus for RAG and golden set.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both agents run end-to-end locally (docker-compose stack up) with real LLM calls when `.env` is configured, and with the fake provider in tests.
- **SC-002**: 100% of emitted agent outputs are schema-valid; unvalidated output is never emitted (enforced by tests).
- **SC-003**: 100% of out-of-scope tool calls are refused and traced (enforced by tests).
- **SC-004**: The evaluation harness produces a report populating all three metrics over the golden set, and a written RAG-vs-fine-tuning analysis is derived from it.
- **SC-005**: Adding a third agent requires only a new spec YAML + prompt (no change under `src/arp/registry`, `src/arp/policy`, `src/arp/orchestration`), demonstrated by test.
- **SC-006**: `terraform validate` passes and the Dockerfile builds.
- **SC-007**: A non-technical stakeholder, using only a browser, can trigger a sensitive-intent question and see the refusal, its reason, and the run's traced events — without reading a log file or a terminal.
- **SC-008**: Run events reach the UI while the run is still in progress, not batched at completion (enforced by asserting the streamed frame sequence in tests).

## Assumptions

- The demo host has Docker and `uv`; Python 3.11 is provisioned via `uv`.
- A GCP project + `gcloud` ADC (or a Gemini API key) is available for live demos; otherwise the local fallback provider is used.
- `terraform` (or OpenTofu) is installed before running the IaC validation step; if absent, IaC is written but not validated locally.
- All catalogue data is synthetic and generated locally; there is no dependency on any external customer system.
- Deployment to GCP, contextual image generation, and executing a real fine-tune are explicitly out of scope for this POC (phase 2).
- The web console is a demonstration surface, not a product: no authentication, no multi-turn
  conversation state, no user accounts. This is a deliberate cut, and it is also the single
  largest gap to production — an unauthenticated endpoint that invokes paid models is an open
  budget. Nothing here may be exposed publicly as-is.
- Node.js 20+ is available for the front-end toolchain; the definition of done therefore spans
  both `make lint && make test` and the front-end's own type-check and lint.
