"""The demo CLI. Routing and rendering only — the graphs have their own tests."""

import pytest

from arp.agents.customer_assistant.schema import AssistantReply
from arp.cli import _render, main


def test_ask_joins_a_multi_word_question(monkeypatch):
    """Unquoted shell words must not silently truncate the question."""
    seen = {}

    async def fake_ask(question):
        seen["question"] = question
        return {"output": AssistantReply(answer="ok")}

    monkeypatch.setattr("arp.cli._ask", fake_ask)
    main(["ask", "Où", "en", "est", "o002", "?"])
    assert seen["question"] == "Où en est o002 ?"


def test_enrich_routes_to_the_enricher(monkeypatch):
    seen = {}

    async def fake_enrich(product_id):
        seen["id"] = product_id
        return {"output": None, "escalated": False}

    monkeypatch.setattr("arp.cli._enrich", fake_enrich)
    main(["enrich", "p003"])
    assert seen["id"] == "p003"


def test_an_unknown_command_is_rejected():
    with pytest.raises(SystemExit):
        main(["dance"])


def test_render_reports_escalation_and_its_reason(capsys):
    _render({"escalated": True, "reason": "sensitive intent: remboursement"})
    out = capsys.readouterr().out
    assert "ESCALADE" in out
    assert "remboursement" in out


def test_render_shows_the_tools_that_were_called(capsys):
    """Which MCP tools ran is the point of the demo, not a detail."""
    _render({"output": AssistantReply(answer="ok"), "tools_used": ["lookup_order"]})
    out = capsys.readouterr().out
    assert "lookup_order" in out
    assert "ok" in out


def test_render_survives_an_escalation_with_no_output(capsys):
    _render({"escalated": True, "reason": None, "output": None})
    assert "non précisée" in capsys.readouterr().out
