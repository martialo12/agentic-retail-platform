import pytest
from pydantic import ValidationError

from arp.agents import AGENTS_DIR
from arp.agents.customer_assistant.schema import AssistantReply
from arp.policy import PolicyError, authorize, is_allowed
from arp.registry import load_agent

VALID = {
    "answer": "Votre commande o1 a été expédiée.",
    "tool_calls_used": ["lookup_order"],
    "escalate": False,
}


@pytest.fixture
def spec():
    return load_agent("customer-assistant", AGENTS_DIR)


def test_accepts_a_valid_reply():
    reply = AssistantReply.model_validate(VALID)
    assert reply.tool_calls_used == ["lookup_order"]
    assert reply.escalate is False


def test_rejects_blank_answer():
    with pytest.raises(ValidationError):
        AssistantReply.model_validate({**VALID, "answer": "  "})


def test_tool_calls_default_to_empty():
    reply = AssistantReply.model_validate({"answer": "Bonjour.", "escalate": False})
    assert reply.tool_calls_used == []


def test_escalate_defaults_to_false():
    assert AssistantReply.model_validate({"answer": "Bonjour."}).escalate is False


def test_reply_is_immutable():
    with pytest.raises(ValidationError):
        AssistantReply.model_validate(VALID).answer = "autre"


# --- registry + policy -----------------------------------------------------


def test_spec_grants_the_three_read_tools(spec):
    assert set(spec.allowed_tools) == {"lookup_order", "get_product", "search_catalog"}


def test_spec_is_denied_the_write_tool(spec):
    """US2: the assistant answers, it never writes. Policy is what enforces that."""
    assert is_allowed(spec, "write_enrichment") is False
    with pytest.raises(PolicyError):
        authorize(spec, "write_enrichment")


def test_enricher_and_assistant_differ_only_by_declaration():
    """Same registry, same policy code — the difference is entirely in the YAML."""
    enricher = load_agent("product-enricher", AGENTS_DIR)
    assistant = load_agent("customer-assistant", AGENTS_DIR)
    assert is_allowed(enricher, "write_enrichment") is True
    assert is_allowed(assistant, "write_enrichment") is False
    assert type(enricher) is type(assistant)


def test_spec_declares_sensitive_intents(spec):
    assert spec.escalation.sensitive_intents
