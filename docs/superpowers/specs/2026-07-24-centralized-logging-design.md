# Centralized logging + per-request tracking (Loguru)

**Date:** 2026-07-24
**Status:** Implemented

## Problem

The run tracer wrote one JSONL file per run to a hardcoded `logs/runs/`. In the
container the process runs as a non-root user against a read-only working
directory, so the first run crashed with `PermissionError: [Errno 13] Permission
denied: 'logs'` — surfaced in the console as an `ÉCHEC` on every question. There
was also **no application logging** at all (no `logging`/`loguru` anywhere),
making requests impossible to trace.

## Decision

- **Loguru** as the single logging pipeline, configured once at process start via
  `arp.observability.logging.configure_logging()`. Output is **stdout only**
  (`LOG_FORMAT=json` in containers, `console` in dev). stdlib + uvicorn records are
  routed in through an `InterceptHandler`. This is the 12-factor / Cloud Run model:
  the platform collects stdout; the app never owns log files.
- **Per-request tracking** via `RequestContextMiddleware` (pure ASGI, so it does not
  buffer the SSE streams). It reads or generates an `x-request-id`, binds it to the
  log context for the whole request, echoes it back as a response header, and logs
  request start/end with method, path, status and duration.
- **Audit trace (FR-009) becomes cloud-native.** The per-run record is emitted as one
  structured stdout line (the durable audit artefact, collected by Cloud Logging) and
  indexed in the run store. The JSONL **file** is now opt-in: written only when
  `RUN_TRACE_DIR` points at a writable directory. Default = no file → the container
  crash is impossible by construction. Run runs bind `run_id` to the log context so
  HTTP requests and agent runs correlate.

## Components

| Unit | Responsibility |
|------|----------------|
| `arp/observability/logging.py` | `configure_logging()`, `InterceptHandler`, formats |
| `arp/api/middleware.py` | `RequestContextMiddleware` — request id + timing |
| `arp/llmops/tracing.py` | emits the audit record to stdout + store; file opt-in |
| `arp/config.py` | `log_level`, `log_format`, `log_diagnose`, `run_trace_dir` |

Instrumentation added at key seams: policy refusals (WARNING), MCP tool calls,
Gemini retries, RAG retrieval, agent-spec loading, escalation decisions, and the
streaming run lifecycle.

## Backward compatibility

`trace_run(..., runs_dir=<path>)` still writes a file when a directory is passed
explicitly, so the existing tracing/agent tests are unchanged. Only the *default*
(no `runs_dir`, no `RUN_TRACE_DIR`) changed: from "write to `logs/runs/`" to
"emit to stdout, write no file".

## Security note

`diagnose`/`backtrace` (which dump local variables into tracebacks and can leak
secrets) are disabled unless `LOG_DIAGNOSE=true` — never on in a container.
