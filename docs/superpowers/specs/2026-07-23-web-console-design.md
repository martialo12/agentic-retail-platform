# Web console for the agentic socle — design

**Date**: 2026-07-23
**Covers**: FR-015..018, SC-007..008
**Status**: validated, not yet planned

## Why

The socle's value is governance: authorization, escalation, auditability. Today that
evidence lives in `make ask` output and JSONL files — legible to engineers, invisible to
a buyer. This adds a surface that makes the guarantees watchable.

The demo that matters is not "an agent answers a question". It is: *ask for a refund, and
watch the run stop before the model is ever called.*

## Scope

Three views, one API, one new store. Explicitly **not** a product: no auth, no accounts, no
multi-turn state.

| View | What it proves |
|---|---|
| `/` Assistant | chat + live socle panel: MCP tools used, refusals, escalation |
| `/enrichissement` | before/after on a sheet, confidence, escalation threshold |
| `/observabilite` | filterable run table, per-run timeline, eval metrics |

## Architecture

```
front/                     Vue 3 + Vuetify + Pinia + Vite/TS   (new)
src/arp/api/               FastAPI                              (new)
src/arp/llmops/run_store.py  AlloyDB-compatible run index       (new)
src/arp/llmops/tracing.py    + optional real-time sink          (modified)
infra/                     +1 Cloud Run service, +1 K8s deploy  (modified)
```

`src/arp/{agents,registry,policy,orchestration,mcp}` are **untouched**. That is load-bearing:
SC-005 claims a new agent needs no socle change, and a UI must not quietly break that claim.

### The API does not call the MCP server over HTTP

It wires `ToolClient(build_server(repo), spec, tracer)` in-process, exactly as `arp/cli.py`
already does. The standalone MCP HTTP server remains, for external MCP clients. Two surfaces,
different consumers, no call between them.

## The one invasive change: real-time tracing

`RunTracer.event()` currently accumulates in memory and writes JSONL on close. Streaming needs
events emitted as they happen.

```python
with trace_run(spec.id, provider=..., sink=queue.put_nowait) as tracer:
```

Additive: `sink=None` by default, JSONL behaviour unchanged, existing tests unaffected. The
tracer stays synchronous — nodes call it from async code, but `put_nowait` does not block.

## API surface

| Endpoint | Shape |
|---|---|
| `POST /api/assistant/ask` | `text/event-stream` |
| `POST /api/enricher/enrich` | `text/event-stream` |
| `GET /api/runs?agent=&outcome=` | paginated list |
| `GET /api/runs/{run_id}` | event timeline |
| `GET /api/catalogue` | sheets, for the enrichment view |
| `GET /api/health` | liveness |

Stream frames mirror the tracer's event kinds, terminated by `[DONE]`:

```
data: {"kind":"retrieval","hits":3}
data: {"kind":"tool_call","tool":"lookup_order","refused":false}
data: {"kind":"llm_call","attempt":1,"valid":true}
data: {"kind":"output","escalate":false,"answer":"…"}
data: [DONE]
```

## Run persistence

New table `runs`: `run_id`, `agent_id`, `provider`, `started_at`, `outcome`, `escalated`,
`events` (jsonb). Served by `RunStore`, shaped like `VectorStore` and held to the same
AlloyDB-compatible SQL constraint.

**The JSONL is not replaced.** It remains the audit artefact (FR-009); the table is a read
index for the observability view. If the store is unreachable, the run still completes and is
still auditable — only the UI degrades.

## Data flow (assistant)

```
EventSource → POST /api/assistant/ask
    → FastAPI creates an asyncio.Queue
    → graph.ainvoke launched as a task, tracer sink pushes each event
    → StreamingResponse yields frames
    → Pinia store updates → panel animates
```

## Error handling

- **Escalation is not an error.** It is a first-class outcome with its own rendering. This is
  the point of the demo; treating it as a failure state would invert the message.
- Provider unavailable → `kind=error` frame, then `[DONE]`; the UI states the failure plainly.
- Client disconnects → the task is cancelled; no orphaned run continues.
- Run store down → run completes, JSONL written, observability view degrades only.

## Testing

- **API**: httpx ASGI transport + `FakeProvider`; assert the *sequence* of SSE frames, not just
  status codes. A batched stream that arrives all at once must fail the test (SC-008).
- **RunStore**: gated on `DATABASE_URL`, like the existing pgvector tests.
- **Front**: `vue-tsc` type-check + eslint, plus a small number of component tests. Full
  front-end coverage is deliberately out of scope for a socle POC — stating that is more
  honest than pretending otherwise.

## Definition of done changes

`make lint && make test` no longer covers the repo. It becomes:

```
make lint && make test && make front-lint && make front-typecheck
```

`CLAUDE.md` must be updated in the same change, or its stated rule becomes false.

## Deliberate cuts

No authentication, no multi-turn conversation state, no analytics dashboard.

The missing authentication is the single largest gap to production: an unauthenticated
endpoint that invokes paid models is an open budget. Acceptable for a local demo, disqualifying
for anything reachable from a network.

FR-018 makes the IaC carry that constraint rather than a README warning: the API's Cloud Run
service declares internal ingress and an empty invoker set, exactly as the MCP service does.
The configuration cannot accidentally publish it. Granting an invoker is the deliberate act
that must wait for authentication.

## Risks

- **Effort skews to the front.** Roughly half the work is Vue, not socle. If the client deadline
  tightens, `/observabilite` is the first view to cut: it is the most expensive to build and the
  least legible to a non-technical audience.
- **Streaming couples the tracer to a transport concern.** Mitigated by keeping the sink a plain
  callable the tracer knows nothing about.
