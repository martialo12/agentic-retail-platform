"""Run tracing (FR-009): one timestamped JSONL record per run.

Auditability is a first-class requirement here, not a debugging aid — the record
is what an AI-Act-style review would read. Hence: one file per run, one line,
ordered events, and an explicit outcome even when the run blows up.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

DEFAULT_RUNS_DIR = Path("logs/runs")


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


@contextmanager
def trace_run(
    agent_id: str,
    runs_dir: Path | None = None,
    provider: str | None = None,
    sink: Callable[[dict[str, Any]], None] | None = None,
) -> Iterator[RunTracer]:
    runs_dir = Path(runs_dir or DEFAULT_RUNS_DIR)
    run_id = uuid.uuid4().hex[:12]
    tracer = RunTracer(agent_id, run_id, provider, sink)
    outcome, error = "completed", None
    try:
        yield tracer
    except BaseException as exc:  # noqa: BLE001 - traced, then re-raised untouched
        outcome, error = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if outcome != "failed" and tracer.escalated:
            outcome = "escalated"
        runs_dir.mkdir(parents=True, exist_ok=True)
        stamp = tracer.started_at.strftime("%Y%m%dT%H%M%S%f")
        path = runs_dir / f"{stamp}-{agent_id}-{run_id}.jsonl"
        payload = json.dumps(tracer.record(outcome, error), ensure_ascii=False)
        path.write_text(payload + "\n", encoding="utf-8")
