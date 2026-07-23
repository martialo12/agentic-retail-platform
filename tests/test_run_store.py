"""The run index (FR-016).

The JSONL file stays the audit artefact; this is a read index so the console can
filter and paginate without re-reading every file — and so observability survives
an ephemeral container filesystem.
"""

import os

import pytest

from arp.llmops.run_store import InMemoryRunStore, PgRunStore, RunSummary

RECORD = {
    "run_id": "r1",
    "agent_id": "customer-assistant",
    "timestamp": "2026-07-23T10:00:00+00:00",
    "provider": "gemini",
    "outcome": "escalated",
    "error": None,
    "events": [
        {"kind": "tool_call", "at": "2026-07-23T10:00:01+00:00", "tool": "lookup_order"},
        {"kind": "escalation", "at": "2026-07-23T10:00:02+00:00", "reason": "remboursement"},
    ],
}


@pytest.fixture
def store():
    return InMemoryRunStore()


def test_saved_run_is_summarised(store):
    store.save(RECORD)
    (summary,) = store.list()
    assert summary == RunSummary(
        run_id="r1",
        agent_id="customer-assistant",
        provider="gemini",
        started_at=summary.started_at,
        outcome="escalated",
        escalated=True,
        event_count=2,
    )


def test_escalated_is_derived_from_the_outcome(store):
    """One source of truth: the tracer already decided, so never recompute it."""
    store.save({**RECORD, "outcome": "completed", "events": []})
    assert store.list()[0].escalated is False


def test_list_filters_by_agent(store):
    store.save(RECORD)
    store.save({**RECORD, "run_id": "r2", "agent_id": "product-enricher"})
    assert [s.run_id for s in store.list(agent="product-enricher")] == ["r2"]


def test_list_filters_by_outcome(store):
    store.save(RECORD)
    store.save({**RECORD, "run_id": "r2", "outcome": "completed"})
    assert [s.run_id for s in store.list(outcome="escalated")] == ["r1"]


def test_list_is_newest_first(store):
    store.save(RECORD)
    store.save({**RECORD, "run_id": "r2", "timestamp": "2026-07-23T11:00:00+00:00"})
    assert [s.run_id for s in store.list()] == ["r2", "r1"]


def test_list_paginates(store):
    for n in range(5):
        store.save({**RECORD, "run_id": f"r{n}", "timestamp": f"2026-07-23T1{n}:00:00+00:00"})
    assert len(store.list(limit=2)) == 2
    assert store.list(limit=2, offset=2)[0].run_id == "r2"


def test_get_returns_the_whole_record(store):
    store.save(RECORD)
    assert store.get("r1")["events"][1]["reason"] == "remboursement"


def test_get_is_none_for_an_unknown_run(store):
    assert store.get("nope") is None


def test_saving_the_same_run_twice_does_not_duplicate_it(store):
    store.save(RECORD)
    store.save(RECORD)
    assert len(store.list()) == 1


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs a live database")
def test_pg_store_round_trips():
    store = PgRunStore(os.environ["DATABASE_URL"], table="runs_test")
    store.save(RECORD)
    assert store.get("r1")["agent_id"] == "customer-assistant"
    summaries = store.list(agent="customer-assistant")
    assert summaries[0].escalated is True
    assert summaries[0].event_count == 2


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs a live database")
def test_pg_store_upserts_rather_than_failing():
    store = PgRunStore(os.environ["DATABASE_URL"], table="runs_test")
    store.save(RECORD)
    store.save({**RECORD, "outcome": "completed"})
    assert store.get("r1")["outcome"] == "completed"
