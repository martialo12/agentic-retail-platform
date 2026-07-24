"""Run tracing (FR-009): one structured audit record per run.

Auditability is a first-class requirement here, not a debugging aid — the record
is what an AI-Act-style review would read. It is emitted as a single structured
log line to stdout (so the platform's log system is the durable audit store) and
indexed in the run store. A JSONL *file* is written only when a writable
directory is configured — never by default, so a read-only container cannot
crash on it.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from arp.config import get_settings

if TYPE_CHECKING:
    # Type-only: the tracer must not depend on the index at runtime, since the
    # index is optional and the tracer is not.
    from arp.llmops.run_store import RunStore


class EventKind(StrEnum):
    RETRIEVAL = "retrieval"
    TOOL_CALL = "tool_call"
    LLM_CALL = "llm_call"
    ESCALATION = "escalation"
    OUTPUT = "output"


class RunTracer:
    """Accumulates events in memory; the record is written once, on exit.

    An optional `sink` is called with each event as it happens, which is what lets
    a console watch a run unfold instead of reporting on it afterwards.
    """

    def __init__(
        self,
        agent_id: str,
        run_id: str,
        provider: str | None = None,
        sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.run_id = run_id
        self.provider = provider
        self.started_at = datetime.now(UTC)
        self._events: list[dict[str, Any]] = []
        self._sink = sink

    def event(self, kind: EventKind | str, **fields: Any) -> None:
        payload = {
            "kind": EventKind(kind).value,
            "at": datetime.now(UTC).isoformat(),
            **fields,
        }
        self._events.append(payload)
        if self._sink is not None:
            try:
                self._sink(payload)
            except Exception:  # noqa: BLE001
                # A consumer that went away is not the agent's problem. The JSONL
                # record is the audit artefact and must survive regardless.
                pass

    @property
    def escalated(self) -> bool:
        return any(e["kind"] == EventKind.ESCALATION.value for e in self._events)

    def record(self, outcome: str, error: str | None = None) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "timestamp": self.started_at.isoformat(),
            "provider": self.provider,
            "outcome": outcome,
            "error": error,
            "events": self._events,
        }


def _emit_audit(record: dict[str, Any]) -> None:
    """Emit the audit record as one structured line to stdout (the durable store)."""
    level = "ERROR" if record["outcome"] == "failed" else "INFO"
    logger.bind(audit=True, audit_record=record).log(
        level, "run {} {} [{}]", record["run_id"], record["outcome"], record["agent_id"]
    )


def _write_file(runs_dir: Path, record: dict[str, Any], stamp: str) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{stamp}-{record['agent_id']}-{record['run_id']}.jsonl"
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")


@contextmanager
def trace_run(
    agent_id: str,
    runs_dir: Path | None = None,
    provider: str | None = None,
    sink: Callable[[dict[str, Any]], None] | None = None,
    store: RunStore | None = None,
) -> Iterator[RunTracer]:
    # An explicit `runs_dir` still writes a file (tests, local audit). Left None,
    # the file is opt-in via RUN_TRACE_DIR and off by default — no cwd writes.
    if runs_dir is None:
        runs_dir = get_settings().run_trace_dir
    run_id = uuid.uuid4().hex[:12]
    tracer = RunTracer(agent_id, run_id, provider, sink)
    outcome, error = "completed", None
    with logger.contextualize(run_id=run_id, agent_id=agent_id):
        try:
            yield tracer
        except BaseException as exc:  # noqa: BLE001 - traced, then re-raised untouched
            outcome, error = "failed", f"{type(exc).__name__}: {exc}"
            raise
        finally:
            if outcome != "failed" and tracer.escalated:
                outcome = "escalated"
            record = tracer.record(outcome, error)
            _emit_audit(record)
            if runs_dir is not None:
                stamp = tracer.started_at.strftime("%Y%m%dT%H%M%S%f")
                _write_file(Path(runs_dir), record, stamp)
            if store is not None:
                try:
                    store.save(record)
                except Exception:  # noqa: BLE001
                    # The index is a convenience. The audit line is already on
                    # stdout, and no database outage may be allowed to cost it.
                    pass
