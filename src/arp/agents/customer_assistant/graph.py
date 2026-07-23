"""Wire the assistant onto the shared state machine — unchanged from Phase 2."""

from typing import Any

from arp.agents import AGENTS_DIR
from arp.agents.customer_assistant.nodes import (
    AssistantState,
    intent_gate,
    make_draft,
    make_emit,
    make_escalate,
    make_prepare,
)
from arp.llm.provider import LLMProvider
from arp.llmops.tracing import RunTracer
from arp.mcp.client import ToolClient
from arp.orchestration.graph import build_graph
from arp.registry import AgentSpec, prompt_for


def build_assistant(
    spec: AgentSpec,
    provider: LLMProvider,
    client: ToolClient,
    tracer: RunTracer | None = None,
) -> Any:
    prompt = prompt_for(spec, AGENTS_DIR)
    return build_graph(
        prepare=make_prepare(spec, client, tracer),
        draft=make_draft(provider, prompt, tracer),
        check=intent_gate(tracer),
        emit=make_emit(tracer),
        escalate=make_escalate(tracer),
        state_schema=AssistantState,
    )
