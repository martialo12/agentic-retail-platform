"""SC-005 — the socle is unchanged between agents.

The selling point of this repo is that a new agent is a declaration, not a
platform change. These tests are what make that claim falsifiable.
"""

import inspect

import pytest

from arp.agents import AGENTS_DIR
from arp.agents.customer_assistant.graph import build_assistant
from arp.agents.product_enricher.graph import build_enricher
from arp.orchestration import build_graph
from arp.policy import PolicyError, authorize, is_allowed
from arp.registry import AgentSpec, load_agent

FIXTURES = "tests/fixtures/agents"


def test_both_agents_are_built_by_the_same_graph_factory():
    enricher_src = inspect.getsource(build_enricher)
    assistant_src = inspect.getsource(build_assistant)
    assert "build_graph(" in enricher_src and "build_graph(" in assistant_src


def test_both_agents_load_through_the_same_registry():
    enricher = load_agent("product-enricher", AGENTS_DIR)
    assistant = load_agent("customer-assistant", AGENTS_DIR)
    assert isinstance(enricher, AgentSpec) and isinstance(assistant, AgentSpec)
    assert enricher.id != assistant.id


def test_the_same_policy_call_yields_opposite_verdicts():
    """No branching on agent id anywhere: the YAML alone decides."""
    enricher = load_agent("product-enricher", AGENTS_DIR)
    assistant = load_agent("customer-assistant", AGENTS_DIR)
    assert is_allowed(enricher, "write_enrichment") is True
    assert is_allowed(assistant, "write_enrichment") is False


def test_no_socle_module_mentions_a_specific_agent():
    """The strongest form of the claim: grep the socle for agent names."""
    import arp.orchestration.graph as graph_mod
    import arp.policy.authorizer as policy_mod
    import arp.registry.loader as loader_mod
    import arp.registry.models as models_mod

    for module in (graph_mod, policy_mod, loader_mod, models_mod):
        source = inspect.getsource(module)
        assert "product-enricher" not in source, f"{module.__name__} names an agent"
        assert "customer-assistant" not in source, f"{module.__name__} names an agent"
        assert "product_enricher" not in source
        assert "customer_assistant" not in source


def test_a_third_agent_needs_only_a_yaml(tmp_path):
    """SC-005 literally: register a new agent without touching any socle module."""
    (tmp_path / "stock-checker.yaml").write_text(
        "id: stock-checker\n"
        "model: gemini-3.5-flash\n"
        "owner: someone@example.com\n"
        "prompt_path: prompt.md\n"
        "allowed_tools:\n"
        "  - get_product\n"
        "escalation:\n"
        "  min_confidence: 0.5\n",
        encoding="utf-8",
    )
    spec = load_agent("stock-checker", tmp_path)
    assert spec.id == "stock-checker"
    assert is_allowed(spec, "get_product") is True
    with pytest.raises(PolicyError):
        authorize(spec, "write_enrichment")


def test_build_graph_signature_is_agent_agnostic():
    params = set(inspect.signature(build_graph).parameters)
    assert params == {"prepare", "draft", "check", "emit", "escalate", "state_schema"}
