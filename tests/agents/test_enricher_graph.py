import json

import pytest

from arp.agents import AGENTS_DIR
from arp.agents.product_enricher.graph import build_enricher
from arp.agents.product_enricher.schema import EnrichedProduct
from arp.llm.provider import FakeProvider
from arp.llmops.tracing import trace_run
from arp.mcp.client import ToolClient
from arp.mcp.repository import InMemoryRepository
from arp.mcp.server import build_server
from arp.models import CatalogueItem
from arp.policy import PolicyError
from arp.rag.ingest import ingest
from arp.rag.retriever import Retriever
from arp.rag.store import InMemoryVectorStore
from arp.registry import load_agent

ITEMS = [
    CatalogueItem(
        id="p1", title="Chaise en chêne massif", specs={"matiere": "chêne"}, category="mobilier"
    ),
    CatalogueItem(id="p2", title="Table basse en verre", specs={}, category="mobilier"),
]

SHEET = {"id": "p2", "title": "Table basse en verre", "specs": {}}

CONFIDENT = EnrichedProduct(
    category="mobilier",
    materials=["verre trempé"],
    use_cases=["salon"],
    seo_description="Table basse en verre trempé pour salon.",
    confidence=0.92,
)
UNSURE = CONFIDENT.model_copy(update={"confidence": 0.2})


@pytest.fixture
def spec():
    return load_agent("product-enricher", AGENTS_DIR)


@pytest.fixture
def repo():
    return InMemoryRepository(items=list(ITEMS))


@pytest.fixture
def retriever():
    provider = FakeProvider()
    store = InMemoryVectorStore()
    ingest(provider, store, ITEMS)
    return Retriever(store, provider)


async def _run(spec, repo, retriever, provider, runs_dir, sheet=SHEET):
    """The trace context must span the invocation: the record is written on exit,
    so returning the graph from inside it would capture an empty run."""
    with trace_run(spec.id, runs_dir=runs_dir, provider="fake") as tracer:
        client = ToolClient(build_server(repo), spec, tracer)
        graph = build_enricher(spec, provider, retriever, client, tracer)
        return await graph.ainvoke({"sheet": sheet})


def _trace(runs_dir):
    return json.loads(next(runs_dir.glob("*.jsonl")).read_text())


async def test_confident_draft_is_emitted_and_written(spec, repo, retriever, tmp_path):
    state = await _run(spec, repo, retriever, FakeProvider(responses=[CONFIDENT]), tmp_path)
    assert state["output"] == CONFIDENT
    assert state["escalated"] is False
    assert repo.get_enrichment("p2")["category"] == "mobilier"


async def test_low_confidence_escalates_and_writes_nothing(spec, repo, retriever, tmp_path):
    state = await _run(spec, repo, retriever, FakeProvider(responses=[UNSURE]), tmp_path)
    assert state["escalated"] is True
    assert state["output"] is None
    assert repo.get_enrichment("p2") is None, "an escalated run must never persist"


async def test_retrieval_context_reaches_the_state(spec, repo, retriever, tmp_path):
    state = await _run(spec, repo, retriever, FakeProvider(responses=[CONFIDENT]), tmp_path)
    assert state["context"], "the draft must be grounded in retrieved catalogue items"


async def test_run_is_fully_traced(spec, repo, retriever, tmp_path):
    await _run(spec, repo, retriever, FakeProvider(responses=[CONFIDENT]), tmp_path)
    kinds = [e["kind"] for e in _trace(tmp_path)["events"]]
    assert "retrieval" in kinds and "llm_call" in kinds
    assert "tool_call" in kinds and "output" in kinds


async def test_escalation_is_traced_and_marks_the_outcome(spec, repo, retriever, tmp_path):
    await _run(spec, repo, retriever, FakeProvider(responses=[UNSURE]), tmp_path)
    record = _trace(tmp_path)
    assert record["outcome"] == "escalated"
    assert any(e["kind"] == "escalation" for e in record["events"])


async def test_out_of_scope_tool_is_refused_and_traced(spec, repo, tmp_path):
    """FR-004: the policy layer, not the tool, is what stops the call."""
    with trace_run(spec.id, runs_dir=tmp_path) as tracer:
        client = ToolClient(build_server(repo), spec, tracer)
        with pytest.raises(PolicyError):
            await client.call("lookup_order", order_id="o1")
    refusals = [e for e in _trace(tmp_path)["events"] if e["kind"] == "tool_call"]
    assert refusals and refusals[0]["refused"] is True


async def test_permitted_tool_call_is_traced_as_allowed(spec, repo, tmp_path):
    with trace_run(spec.id, runs_dir=tmp_path) as tracer:
        client = ToolClient(build_server(repo), spec, tracer)
        assert (await client.call("get_product", product_id="p1"))["id"] == "p1"
    event = [e for e in _trace(tmp_path)["events"] if e["kind"] == "tool_call"][0]
    assert event["refused"] is False and event["tool"] == "get_product"


class AlwaysInvalidProvider:
    """A model that never produces schema-valid output."""

    def __init__(self):
        self.attempts = 0

    def complete(self, messages, schema):
        self.attempts += 1
        raise ValueError("not valid against the schema")

    def embed(self, texts):
        return [[0.0] for _ in texts]


async def test_unparsable_output_retries_then_escalates(spec, repo, retriever, tmp_path):
    """FR-008: bounded retry, then escalate — never emit unvalidated output."""
    from arp.agents.product_enricher.nodes import MAX_ATTEMPTS

    provider = AlwaysInvalidProvider()
    state = await _run(spec, repo, retriever, provider, tmp_path)
    assert provider.attempts == MAX_ATTEMPTS
    assert state["escalated"] is True
    assert state["output"] is None
    assert repo.get_enrichment("p2") is None
    assert "schema validation failed" in state["reason"]
