"""Vector storage (FR-006).

Two implementations behind one protocol: an in-memory store for unit tests, and
pgvector for the real thing. The SQL is deliberately plain pgvector — the same
statements run unchanged on AlloyDB in production.
"""

from __future__ import annotations

import json
import math
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Hit(BaseModel):
    id: str
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


@runtime_checkable
class VectorStore(Protocol):
    def upsert(self, id: str, text: str, embedding: list[float], metadata: dict) -> None: ...

    def search(self, embedding: list[float], k: int) -> list[Hit]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class InMemoryVectorStore:
    """Unit-test double. Same semantics as pgvector: cosine similarity, top-k."""

    def __init__(self) -> None:
        self._rows: dict[str, tuple[str, list[float], dict]] = {}

    def __len__(self) -> int:
        return len(self._rows)

    def upsert(self, id: str, text: str, embedding: list[float], metadata: dict) -> None:
        self._rows[id] = (text, embedding, metadata)

    def search(self, embedding: list[float], k: int) -> list[Hit]:
        scored = [
            Hit(id=key, text=text, score=_cosine(embedding, vec), metadata=meta)
            for key, (text, vec, meta) in self._rows.items()
        ]
        return sorted(scored, key=lambda h: h.score, reverse=True)[:k]


class PgVectorStore:
    """pgvector-backed store. SQL kept AlloyDB-compatible (no vendor extensions)."""

    def __init__(self, dsn: str, table: str = "documents", dim: int | None = None) -> None:
        """`dim=None` means: adopt whatever width the configured embedding model
        emits. Hardcoding a width silently breaks the day the model changes."""
        self._dsn = dsn
        self._table = table
        self._dim = dim
        if dim is not None:
            self._ensure_schema(dim)

    def _connect(self):
        import psycopg
        from pgvector.psycopg import register_vector

        conn = psycopg.connect(self._dsn, autocommit=True)
        register_vector(conn)
        return conn

    def _ensure_schema(self, dim: int) -> None:
        import psycopg

        with psycopg.connect(self._dsn, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} ("
                "  id TEXT PRIMARY KEY,"
                "  content TEXT NOT NULL,"
                "  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,"
                f" embedding vector({dim})"
                ")"
            )

    def dimension(self) -> int | None:
        """Width the table was actually created with, or None if it does not exist."""
        import psycopg

        with psycopg.connect(self._dsn, autocommit=True) as conn:
            row = conn.execute(
                "SELECT a.atttypmod FROM pg_attribute a"
                " JOIN pg_class c ON c.oid = a.attrelid"
                " WHERE c.relname = %s AND a.attname = 'embedding'",
                (self._table,),
            ).fetchone()
        return int(row[0]) if row else None

    def drop(self) -> None:
        import psycopg

        with psycopg.connect(self._dsn, autocommit=True) as conn:
            conn.execute(f"DROP TABLE IF EXISTS {self._table}")

    def reset(self) -> None:
        import psycopg

        with psycopg.connect(self._dsn, autocommit=True) as conn:
            conn.execute(f"TRUNCATE {self._table}")

    def __len__(self) -> int:
        if self.dimension() is None:
            return 0
        with self._connect() as conn:
            return conn.execute(f"SELECT count(*) FROM {self._table}").fetchone()[0]

    def upsert(self, id: str, text: str, embedding: list[float], metadata: dict) -> None:
        import numpy as np

        width = len(embedding)
        existing = self.dimension()
        if existing is None:
            self._ensure_schema(width)
        elif existing != width:
            raise ValueError(
                f"embedding dimension mismatch: table '{self._table}' stores "
                f"vector({existing}) but the model emitted {width}. The embedding "
                "model changed — recreate the table (drop()) or pin EMBED_DIM."
            )

        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO {self._table} (id, content, metadata, embedding)"
                " VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (id) DO UPDATE SET"
                "   content = EXCLUDED.content,"
                "   metadata = EXCLUDED.metadata,"
                "   embedding = EXCLUDED.embedding",
                (id, text, json.dumps(metadata), np.array(embedding, dtype=np.float32)),
            )

    def search(self, embedding: list[float], k: int) -> list[Hit]:
        import numpy as np

        vec = np.array(embedding, dtype=np.float32)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT id, content, metadata, 1 - (embedding <=> %s) AS score"
                f" FROM {self._table} ORDER BY embedding <=> %s LIMIT %s",
                (vec, vec, k),
            ).fetchall()
        return [Hit(id=r[0], text=r[1], metadata=r[2] or {}, score=float(r[3])) for r in rows]
