import json

import pytest
from arp.agents.customer_assistant.graph import build_assistant

from arp.agents import AGENTS_DIR
from arp.agents.customer_assistant.schema import AssistantReply
from arp.llm.provider import FakeProvider
from arp.llmops.tracing import trace_run
from arp.mcp.client import ToolClient
from arp.mcp.repository import InMemoryRepository
from arp.mcp.server import build_server
from arp.models import CatalogueItem, Order
from arp.policy import PolicyError
from arp.registry import load_agent

ITEMS = [CatalogueItem(id="p1", title="Chaise en chêne", specs={}, category="mobilier")]
ORDERS = [Order(id="o1", status="expédiée", product_ids=["p1"], customer_ref="c-001")]

ANSWERED = AssistantReply(
    answer="Votre commande o1 a été expédiée.", tool_calls_used=["lookup_order"], escalate=False
)
SELF_ESCALATED = AssistantReply(answer="Je passe la main.", escalate=True)


@pytest.fixture
def spec():
    return load_agent("customer-assistant", AGENTS_DIR)


@pytest.fixture
def repo():
    return InMemoryRepository(items=list(ITEMS), orders=list(ORDERS))


async def _ask(spec, repo, provider, runs_dir, question):
    with trace_run(spec.id, runs_dir=runs_dir, provider="fake") as tracer:
        client = ToolClient(build_server(repo), spec, tracer)
        graph = build_assistant(spec, provider, client, tracer)
        return await graph.ainvoke({"question": question})


def _trace(runs_dir):
    return json.loads(next(runs_dir.glob("*.jsonl")).read_text())


async def test_order_question_calls_lookup_order_through_mcp(spec, repo, tmp_path):
    state = await _ask(
        spec, repo, FakeProvider(responses=[ANSWERED]), tmp_path, "Où en est ma commande o1 ?"
    )
    assert "lookup_order" in state["tools_used"]
    assert state["output"] == ANSWERED
    assert state["escalated"] is False
    tools = [e["tool"] for e in _trace(tmp_path)["events"] if e["kind"] == "tool_call"]
    assert "lookup_order" in tools


async def test_product_question_calls_get_product(spec, repo, tmp_path):
    state = await _ask(
        spec, repo, FakeProvider(responses=[ANSWERED]), tmp_path, "Le produit p1 est-il dispo ?"
    )
    assert "get_product" in state["tools_used"]


async def test_free_text_question_falls_back_to_search(spec, repo, tmp_path):
    state = await _ask(
        spec, repo, FakeProvider(responses=[ANSWERED]), tmp_path, "vous avez des chaises ?"
    )
    assert "search_catalog" in state["tools_used"]


async def test_sensitive_intent_escalates_before_answering(spec, repo, tmp_path):
    """Declared in spec.yaml, not in code: escalation policy is configuration."""
    state = await _ask(
        spec, repo, FakeProvider(responses=[ANSWERED]), tmp_path, "je veux un remboursement"
    )
    assert state["escalated"] is True
    assert state["output"] is None
    record = _trace(tmp_path)
    assert record["outcome"] == "escalated"
    assert any(e["kind"] == "escalation" for e in record["events"])


async def test_model_can_escalate_itself(spec, repo, tmp_path):
    state = await _ask(
        spec, repo, FakeProvider(responses=[SELF_ESCALATED]), tmp_path, "question ambiguë"
    )
    assert state["escalated"] is True
    assert state["output"] is None


async def test_write_tool_is_refused_by_policy_and_traced(spec, repo, tmp_path):
    """US2 acceptance scenario 2: the assistant cannot write, and the refusal is traced."""
    with trace_run(spec.id, runs_dir=tmp_path) as tracer:
        client = ToolClient(build_server(repo), spec, tracer)
        with pytest.raises(PolicyError):
            await client.call("write_enrichment", product_id="p1", attributes={})
    event = [e for e in _trace(tmp_path)["events"] if e["kind"] == "tool_call"][0]
    assert event["refused"] is True and event["tool"] == "write_enrichment"
    assert repo.get_enrichment("p1") is None


async def test_run_is_traced_end_to_end(spec, repo, tmp_path):
    await _ask(spec, repo, FakeProvider(responses=[ANSWERED]), tmp_path, "commande o1 ?")
    kinds = [e["kind"] for e in _trace(tmp_path)["events"]]
    assert "tool_call" in kinds and "llm_call" in kinds and "output" in kinds
