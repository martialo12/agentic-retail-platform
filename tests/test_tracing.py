import json

import pytest

from arp.llmops.tracing import EventKind, RunTracer, trace_run


@pytest.fixture
def runs_dir(tmp_path):
    return tmp_path / "runs"


def _records(runs_dir):
    files = sorted(runs_dir.glob("*.jsonl"))
    return [json.loads(line) for f in files for line in f.read_text().splitlines() if line]


def test_a_run_writes_exactly_one_record(runs_dir):
    with trace_run("product-enricher", runs_dir=runs_dir):
        pass
    assert len(_records(runs_dir)) == 1


def test_record_carries_agent_and_timestamp(runs_dir):
    with trace_run("product-enricher", runs_dir=runs_dir):
        pass
    record = _records(runs_dir)[0]
    assert record["agent_id"] == "product-enricher"
    assert record["timestamp"].endswith("+00:00")
    assert record["run_id"]


def test_events_are_recorded_in_order(runs_dir):
    with trace_run("product-enricher", runs_dir=runs_dir) as tracer:
        tracer.event(EventKind.RETRIEVAL, query="chaise", hits=3)
        tracer.event(EventKind.LLM_CALL, provider="fake")
        tracer.event(EventKind.TOOL_CALL, tool="get_product")
        tracer.event(EventKind.OUTPUT, valid=True)
    events = _records(runs_dir)[0]["events"]
    assert [e["kind"] for e in events] == ["retrieval", "llm_call", "tool_call", "output"]
    assert events[0]["query"] == "chaise"


def test_all_spec_event_kinds_exist():
    """FR-009 names the five event kinds the trace must be able to carry."""
    assert {k.value for k in EventKind} == {
        "retrieval",
        "tool_call",
        "llm_call",
        "escalation",
        "output",
    }


def test_escalation_is_recorded(runs_dir):
    with trace_run("product-enricher", runs_dir=runs_dir) as tracer:
        tracer.event(EventKind.ESCALATION, reason="low confidence", confidence=0.2)
    record = _records(runs_dir)[0]
    assert record["events"][0]["kind"] == "escalation"
    assert record["outcome"] == "escalated"


def test_outcome_defaults_to_completed(runs_dir):
    with trace_run("product-enricher", runs_dir=runs_dir) as tracer:
        tracer.event(EventKind.OUTPUT, valid=True)
    assert _records(runs_dir)[0]["outcome"] == "completed"


def test_failure_is_traced_and_reraised(runs_dir):
    with pytest.raises(RuntimeError):
        with trace_run("product-enricher", runs_dir=runs_dir):
            raise RuntimeError("boom")
    record = _records(runs_dir)[0]
    assert record["outcome"] == "failed"
    assert "boom" in record["error"]


def test_serving_provider_is_captured(runs_dir):
    """Edge case in the spec: the trace must say which provider served the run."""
    with trace_run("product-enricher", runs_dir=runs_dir, provider="fake"):
        pass
    assert _records(runs_dir)[0]["provider"] == "fake"


def test_two_runs_write_two_records(runs_dir):
    for _ in range(2):
        with trace_run("product-enricher", runs_dir=runs_dir):
            pass
    assert len(_records(runs_dir)) == 2


def test_record_is_one_json_line(runs_dir):
    with trace_run("product-enricher", runs_dir=runs_dir) as tracer:
        tracer.event(EventKind.OUTPUT, valid=True)
    text = next(runs_dir.glob("*.jsonl")).read_text()
    assert text.count("\n") == 1


def test_tracer_type_is_exposed(runs_dir):
    with trace_run("a", runs_dir=runs_dir) as tracer:
        assert isinstance(tracer, RunTracer)
