"""The shared state machine every agent runs on (FR-005).

`prepare → draft → check → (escalate | emit)`.

The shape is deliberately agent-agnostic: the enricher's `prepare` retrieves
catalogue context, the assistant's understands an intent and calls tools, but
neither owns the graph. That is what makes a second agent a set of nodes rather
than a second platform.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from arp.llmops.tracing import EventKind, RunTracer

Node = Callable[[dict], Awaitable[dict]]


def build_graph(
    prepare: Node,
    draft: Node,
    check: Callable[[dict], str],
    emit: Node,
    escalate: Node,
    state_schema: type = dict,
) -> Any:
    graph = StateGraph(state_schema)
    graph.add_node("prepare", prepare)
    graph.add_node("draft", draft)
    graph.add_node("emit", emit)
    graph.add_node("escalate", escalate)

    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "draft")
    # `check` is the human-in-the-loop gate: it decides, it does not act.
    graph.add_conditional_edges("draft", check, {"emit": "emit", "escalate": "escalate"})
    graph.add_edge("emit", END)
    graph.add_edge("escalate", END)
    return graph.compile()


def confidence_gate(
    min_confidence: float, tracer: RunTracer | None = None
) -> Callable[[dict], str]:
    """Route on the drafted confidence, tracing the escalation decision.

    A missing or unparsable draft escalates too — never emit what was not validated.
    """

    def check(state: dict) -> str:
        draft = state.get("draft")
        confidence = getattr(draft, "confidence", None)
        if draft is None or confidence is None or confidence < min_confidence:
            if tracer is not None:
                tracer.event(
                    EventKind.ESCALATION,
                    reason="no valid draft" if draft is None else "confidence below threshold",
                    confidence=confidence,
                    threshold=min_confidence,
                )
            return "escalate"
        return "emit"

    return check
