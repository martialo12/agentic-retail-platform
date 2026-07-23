"""The assistant's steps: `understand + maybe_tool → answer → (escalate | emit)`.

The intent gate lives here rather than in `orchestration/`, because escalating on
a refund request is this agent's concern — not the socle's.
"""

import re
from typing import TypedDict

from pydantic import ValidationError

from arp.agents.customer_assistant.schema import AssistantReply
from arp.llm.provider import LLMProvider
from arp.llmops.tracing import EventKind, RunTracer
from arp.mcp.client import ToolClient
from arp.registry import AgentSpec
from arp.text import normalize
from arp.tools import GET_PRODUCT, LOOKUP_ORDER, SEARCH_CATALOG

MAX_ATTEMPTS = 3

ORDER_REF = re.compile(r"\bo\d+\b", re.IGNORECASE)
PRODUCT_REF = re.compile(r"\bp\d+\b", re.IGNORECASE)


class AssistantState(TypedDict, total=False):
    question: str
    facts: list[dict]
    tools_used: list[str]
    sensitive: bool
    draft: AssistantReply | None
    output: AssistantReply | None
    escalated: bool
    reason: str | None


def detect_sensitive(question: str, intents: list[str]) -> str | None:
    """Match declared sensitive intents against the question.

    Kept deliberately literal: a refund request must escalate even when the model
    is confident it can answer, so this decision must not depend on the model.
    """
    haystack = normalize(question)
    for intent in intents:
        if normalize(intent) in haystack:
            return intent
    return None


def make_prepare(spec: AgentSpec, client: ToolClient, tracer: RunTracer | None):
    """`understand` + `maybe_tool`: resolve references, then fetch through MCP."""

    async def prepare(state: AssistantState) -> dict:
        question = state["question"]
        intent = detect_sensitive(question, spec.escalation.sensitive_intents)
        if intent is not None:
            return {
                "sensitive": True,
                "reason": f"sensitive intent: {intent}",
                "facts": [],
                "tools_used": [],
            }

        facts: list[dict] = []
        used: list[str] = []
        if order_id := _first(ORDER_REF, question):
            facts.append(await _safe_call(client, LOOKUP_ORDER, order_id=order_id))
            used.append(LOOKUP_ORDER)
        if product_id := _first(PRODUCT_REF, question):
            facts.append(await _safe_call(client, GET_PRODUCT, product_id=product_id))
            used.append(GET_PRODUCT)
        if not used:
            facts.append(await _safe_call(client, SEARCH_CATALOG, query=question, k=3))
            used.append(SEARCH_CATALOG)

        if tracer is not None:
            tracer.event(EventKind.RETRIEVAL, question=question, tools=used)
        return {"facts": facts, "tools_used": used, "sensitive": False}

    return prepare


def make_draft(provider: LLMProvider, prompt: str, tracer: RunTracer | None):
    async def draft(state: AssistantState) -> dict:
        if state.get("sensitive"):
            return {"draft": None}
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Question du client: {state['question']}\n"
                    f"Résultats des outils: {state.get('facts', [])}"
                ),
            },
        ]
        last_error: str | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                reply = provider.complete(messages, AssistantReply)
            except (ValidationError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if tracer is not None:
                    tracer.event(EventKind.LLM_CALL, attempt=attempt, valid=False, error=last_error)
                continue
            if tracer is not None:
                tracer.event(
                    EventKind.LLM_CALL, attempt=attempt, valid=True, escalate=reply.escalate
                )
            return {"draft": reply}
        return {
            "draft": None,
            "reason": f"schema validation failed after {MAX_ATTEMPTS} attempts: {last_error}",
        }

    return draft


def intent_gate(tracer: RunTracer | None):
    """Route to escalation on a declared sensitive intent, on the model's own
    `escalate` flag, or on no valid draft at all."""

    def check(state: AssistantState) -> str:
        draft = state.get("draft")
        reason = None
        if state.get("sensitive"):
            reason = state.get("reason") or "sensitive intent"
        elif draft is None:
            reason = state.get("reason") or "no valid reply"
        elif draft.escalate:
            reason = "model requested human handover"
        if reason is None:
            return "emit"
        if tracer is not None:
            tracer.event(EventKind.ESCALATION, reason=reason)
        return "escalate"

    return check


def make_emit(tracer: RunTracer | None):
    async def emit(state: AssistantState) -> dict:
        reply = state["draft"]
        if tracer is not None:
            tracer.event(EventKind.OUTPUT, valid=True, tools=state.get("tools_used", []))
        return {"output": reply, "escalated": False}

    return emit


def make_escalate(tracer: RunTracer | None):
    async def escalate(state: AssistantState) -> dict:
        reason = state.get("reason") or "handed over to a human advisor"
        if tracer is not None:
            tracer.event(EventKind.OUTPUT, valid=False, escalated=True, reason=reason)
        return {"escalated": True, "output": None, "reason": reason}

    return escalate


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0).lower() if match else None


async def _safe_call(client: ToolClient, tool: str, **arguments) -> dict:
    """A missing order or product is an answerable fact, not a crash — the model
    is told the lookup failed and declines rather than inventing a status."""
    try:
        return {"tool": tool, "result": await client.call(tool, **arguments)}
    except Exception as exc:  # noqa: BLE001 - surfaced to the model as a fact
        return {"tool": tool, "error": f"{type(exc).__name__}: {exc}"}
