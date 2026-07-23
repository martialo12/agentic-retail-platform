import pytest

from arp.policy import PolicyError, authorize, is_allowed
from arp.registry import AgentSpec, EscalationPolicy

ASSISTANT = AgentSpec(
    id="customer-assistant",
    model="gemini-3.5-flash",
    allowed_tools=["lookup_order", "get_product", "search_catalog"],
    escalation=EscalationPolicy(min_confidence=0.6),
    owner="martial.wafo@example.com",
    prompt_path="prompts/assistant.md",
)


def test_authorize_permits_granted_tool():
    assert authorize(ASSISTANT, "lookup_order") is None


def test_authorize_refuses_ungranted_tool():
    with pytest.raises(PolicyError):
        authorize(ASSISTANT, "write_enrichment")


def test_refusal_carries_structured_context_for_tracing():
    """The refusal must be traceable (FR-004), so it names the agent and the tool."""
    with pytest.raises(PolicyError) as excinfo:
        authorize(ASSISTANT, "write_enrichment")
    assert excinfo.value.agent_id == "customer-assistant"
    assert excinfo.value.tool == "write_enrichment"
    assert "write_enrichment" in str(excinfo.value)


def test_authorize_refuses_tool_outside_catalogue():
    with pytest.raises(PolicyError):
        authorize(ASSISTANT, "drop_database")


@pytest.mark.parametrize(
    ("tool", "expected"),
    [
        ("lookup_order", True),
        ("get_product", True),
        ("search_catalog", True),
        ("write_enrichment", False),
        ("drop_database", False),
    ],
)
def test_is_allowed_matches_spec(tool, expected):
    assert is_allowed(ASSISTANT, tool) is expected


def test_is_allowed_never_raises():
    assert is_allowed(ASSISTANT, "anything") is False
