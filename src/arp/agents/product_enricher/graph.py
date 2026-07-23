"""Wire the enricher's nodes onto the shared state machine."""

from typing import Any

from arp.agents import AGENTS_DIR
from arp.agents.product_enricher.nodes import (
    EnricherState,
    make_draft,
    make_emit,
    make_escalate,
    make_prepare,
)
from arp.llm.provider import LLMProvider
from arp.llmops.tracing import RunTracer
from arp.mcp.client import ToolClient
from arp.orchestration.graph import build_graph, confidence_gate
from arp.rag.retriever import Retriever
from arp.registry import AgentSpec, prompt_for


def build_enricher(
    spec: AgentSpec,
    provider: LLMProvider,
    retriever: Retriever,
    client: ToolClient,
    tracer: RunTracer | None = None,
) -> Any:
    prompt = prompt_for(spec, AGENTS_DIR)
    return build_graph(
        prepare=make_prepare(retriever, tracer),
        draft=make_draft(provider, prompt, tracer),
        check=confidence_gate(spec.escalation.min_confidence, tracer),
        emit=make_emit(client, tracer, spec.escalation.min_confidence),
        escalate=make_escalate(tracer),
        state_schema=EnricherState,
    )
