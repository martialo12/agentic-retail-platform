"""The enricher's four steps. Everything agent-specific lives here."""

from typing import Any, TypedDict

from pydantic import ValidationError

from arp.agents.product_enricher.schema import EnrichedProduct
from arp.llm.provider import LLMProvider
from arp.llmops.tracing import EventKind, RunTracer
from arp.mcp.client import ToolClient
from arp.rag.retriever import Retriever
from arp.tools import WRITE_ENRICHMENT

MAX_ATTEMPTS = 3


class EnricherState(TypedDict, total=False):
    sheet: dict
    context: list[dict]
    draft: EnrichedProduct | None
    output: EnrichedProduct | None
    escalated: bool
    reason: str | None


def _query(sheet: dict) -> str:
    parts = [sheet.get("title", "")]
    parts.extend(f"{k}: {v}" for k, v in sorted((sheet.get("specs") or {}).items()))
    return " | ".join(p for p in parts if p)


def make_prepare(retriever: Retriever, tracer: RunTracer | None, k: int = 3):
    async def prepare(state: EnricherState) -> dict:
        query = _query(state["sheet"])
        hits = retriever.search(query, k=k)
        if tracer is not None:
            tracer.event(EventKind.RETRIEVAL, query=query, hits=len(hits))
        return {"context": [h.model_dump() for h in hits]}

    return prepare


def make_draft(provider: LLMProvider, prompt: str, tracer: RunTracer | None):
    """Bounded retry, then give up and let the gate escalate (FR-008).

    A schema violation is never repaired by hand and never emitted — the draft
    simply stays absent, which routes the run to human review.
    """

    async def draft(state: EnricherState) -> dict:
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Fiche à enrichir: {state['sheet']}\n"
                    f"Contexte catalogue: {state.get('context', [])}"
                ),
            },
        ]
        last_error: str | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                result = provider.complete(messages, EnrichedProduct)
            except (ValidationError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if tracer is not None:
                    tracer.event(EventKind.LLM_CALL, attempt=attempt, valid=False, error=last_error)
                continue
            if tracer is not None:
                tracer.event(
                    EventKind.LLM_CALL, attempt=attempt, valid=True, confidence=result.confidence
                )
            return {"draft": result}
        return {
            "draft": None,
            "reason": f"schema validation failed after {MAX_ATTEMPTS} attempts: {last_error}",
        }

    return draft


def make_emit(client: ToolClient, tracer: RunTracer | None):
    async def emit(state: EnricherState) -> dict:
        draft = state["draft"]
        await client.call(
            WRITE_ENRICHMENT,
            product_id=state["sheet"]["id"],
            attributes=draft.model_dump(),
        )
        if tracer is not None:
            tracer.event(EventKind.OUTPUT, valid=True, confidence=draft.confidence)
        return {"output": draft, "escalated": False}

    return emit


def make_escalate(tracer: RunTracer | None):
    """Hand off to a human. Critically: no tool call, so nothing is persisted."""

    async def escalate(state: EnricherState) -> dict:
        draft = state.get("draft")
        reason = state.get("reason") or "confidence below the spec threshold"
        if tracer is not None:
            tracer.event(EventKind.OUTPUT, valid=False, escalated=True, reason=reason)
        return {
            "escalated": True,
            "output": None,
            "reason": reason,
            "draft": draft,
        }

    return escalate


def initial_state(sheet: dict) -> dict[str, Any]:
    return {"sheet": sheet, "context": [], "draft": None, "output": None, "escalated": False}
