"""A queryable index of past runs (FR-016).

The JSONL file in `logs/runs` remains the audit artefact (FR-009). This table
exists so the console can filter and paginate without re-reading every file, and
so observability survives an ephemeral container filesystem. The two are not
interchangeable: losing the index costs a view, losing the file costs the audit.

SQL is kept AlloyDB-compatible, mirroring `PgVectorStore`.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class RunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    agent_id: str
    provider: str | None
    started_at: datetime
    outcome: str
    escalated: bool
    event_count: int


def _summarise(record: dict[str, Any]) -> RunSummary:
    return RunSummary(
        run_id=record["run_id"],
        agent_id=record["agent_id"],
        provider=record.get("provider"),
        started_at=datetime.fromisoformat(record["timestamp"]),
        outcome=record["outcome"],
        # Derived from the outcome the tracer already decided, never recomputed
        # from the events: two sources of truth would eventually disagree.
        escalated=record["outcome"] == "escalated",
        event_count=len(record.get("events", [])),
    )


@runtime_checkable
class RunStore(Protocol):
    def save(self, record: dict[str, Any]) -> None: ...

    def list(
        self,
        agent: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunSummary]: ...

    def get(self, run_id: str) -> dict[str, Any] | None: ...


class InMemoryRunStore:
    """Reference implementation, and what the API tests run against."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def save(self, record: dict[str, Any]) -> None:
        self._records[record["run_id"]] = dict(record)

    def list(
        self,
        agent: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunSummary]:
        rows = [
            _summarise(record)
            for record in self._records.values()
            if (agent is None or record["agent_id"] == agent)
            and (outcome is None or record["outcome"] == outcome)
        ]
        rows.sort(key=lambda summary: summary.started_at, reverse=True)
        return rows[offset : offset + limit]

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self._records.get(run_id)


class PgRunStore:
    """Postgres/AlloyDB-backed index. No vendor extensions."""

    def __init__(self, dsn: str, table: str = "runs") -> None:
        self._dsn = dsn
        self._table = table
        self._ensure_schema()

    def _connect(self):
        import psycopg

        return psycopg.connect(self._dsn, autocommit=True)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} ("
                "  run_id TEXT PRIMARY KEY,"
                "  agent_id TEXT NOT NULL,"
                "  provider TEXT,"
                "  started_at TIMESTAMPTZ NOT NULL,"
                "  outcome TEXT NOT NULL,"
                "  record JSONB NOT NULL"
                ")"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS {self._table}_started_at_idx "
                f"ON {self._table} (started_at DESC)"
            )

    def save(self, record: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO {self._table} "
                "(run_id, agent_id, provider, started_at, outcome, record) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (run_id) DO UPDATE SET "
                "  outcome = EXCLUDED.outcome, record = EXCLUDED.record",
                (
                    record["run_id"],
                    record["agent_id"],
                    record.get("provider"),
                    record["timestamp"],
                    record["outcome"],
                    json.dumps(record, ensure_ascii=False),
                ),
            )

    def list(
        self,
        agent: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunSummary]:
        clauses: list[str] = []
        params: list[Any] = []
        if agent is not None:
            clauses.append("agent_id = %s")
            params.append(agent)
        if outcome is not None:
            clauses.append("outcome = %s")
            params.append(outcome)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT record FROM {self._table} {where} "
                "ORDER BY started_at DESC LIMIT %s OFFSET %s",
                (*params, limit, offset),
            ).fetchall()
        return [_summarise(row[0]) for row in rows]

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT record FROM {self._table} WHERE run_id = %s", (run_id,)
            ).fetchone()
        return row[0] if row else None
