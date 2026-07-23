from pathlib import Path

import pytest
from pydantic import ValidationError

from arp.registry import AgentSpec, EscalationPolicy, load_agent
from arp.tools import TOOL_CATALOG

FIXTURES = Path(__file__).parent / "fixtures" / "agents"


def test_loads_valid_spec():
    spec = load_agent("demo-agent", FIXTURES)
    assert isinstance(spec, AgentSpec)
    assert spec.id == "demo-agent"
    assert spec.model == "gemini-3.5-flash"
    assert spec.allowed_tools == ["search_catalog", "get_product"]
    assert spec.owner == "martial.wafo@example.com"
    assert spec.prompt_path == "prompts/demo.md"


def test_loads_escalation_policy():
    spec = load_agent("demo-agent", FIXTURES)
    assert isinstance(spec.escalation, EscalationPolicy)
    assert spec.escalation.min_confidence == 0.7
    assert spec.escalation.sensitive_intents == ["refund"]


def test_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        load_agent("missing-field", FIXTURES)


def test_rejects_tool_absent_from_catalogue():
    with pytest.raises(ValueError, match="drop_database"):
        load_agent("unknown-tool", FIXTURES)


def test_raises_on_unknown_agent_id():
    with pytest.raises(FileNotFoundError):
        load_agent("does-not-exist", FIXTURES)


def test_rejects_confidence_outside_unit_interval():
    with pytest.raises(ValidationError):
        EscalationPolicy(min_confidence=1.5)


def test_catalogue_matches_spec_fr003():
    assert TOOL_CATALOG == frozenset(
        {"search_catalog", "get_product", "write_enrichment", "lookup_order"}
    )


def test_spec_is_immutable():
    """A loaded spec is the authority on permissions; it must not be mutated at runtime."""
    spec = load_agent("demo-agent", FIXTURES)
    with pytest.raises(ValidationError):
        spec.allowed_tools = ["write_enrichment"]
