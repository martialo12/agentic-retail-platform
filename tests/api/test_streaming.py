"""SC-008: events must reach the client during the run, not batched at the end."""

import json

import pytest

from arp.api.streaming import sse, stream_run
from arp.api.wiring import build_assistant_graph, build_deps
from arp.config import Settings
from arp.llmops.run_store import InMemoryRunStore


@pytest.fixture
def deps():
    return build_deps(Settings(llm_provider="fake"), run_store=InMemoryRunStore())


def _frames(chunks: list[str]) -> list[dict | str]:
    out: list[dict | str] = []
    for chunk in chunks:
        body = chunk.removeprefix("data: ").strip()
        out.append(body if body == "[DONE]" else json.loads(body))
    return out


async def _collect(deps, state=None) -> list[dict | str]:
    chunks = [
        chunk
        async for chunk in stream_run(
            deps,
            "customer-assistant",
            build_assistant_graph,
            state or {"question": "Où en est ma commande o001 ?"},
        )
    ]
    return _frames(chunks)


def test_sse_formats_a_frame():
    assert sse({"kind": "output"}) == 'data: {"kind": "output"}\n\n'


def test_sse_passes_a_sentinel_through():
    assert sse("[DONE]") == "data: [DONE]\n\n"


def test_sse_keeps_accents_readable():
    """ensure_ascii would turn every French answer into escape sequences."""
    assert "expédiée" in sse({"answer": "expédiée"})


async def test_stream_emits_events_then_a_sentinel(deps):
    frames = await _collect(deps)
    assert frames[-1] == "[DONE]"
    kinds = [f["kind"] for f in frames[:-1] if isinstance(f, dict)]
    assert "tool_call" in kinds
    assert kinds[-1] in {"output", "escalation"}


async def test_a_sensitive_intent_escalates_before_any_model_call(deps):
    """The demo's centrepiece: the run stops before the LLM is ever reached."""
    frames = await _collect(deps, {"question": "Je veux un remboursement pour o001"})
    kinds = [f["kind"] for f in frames[:-1] if isinstance(f, dict)]
    assert "escalation" in kinds
    assert "llm_call" not in kinds


async def test_the_run_is_indexed_after_streaming(deps):
    await _collect(deps)
    assert deps.run_store.list()[0].agent_id == "customer-assistant"


async def test_a_provider_failure_is_streamed_not_swallowed(deps):
    class Exploding:
        def complete(self, messages, schema):
            raise RuntimeError("provider down")

        def embed(self, texts):
            raise RuntimeError("provider down")

    object.__setattr__(deps, "provider", Exploding())
    frames = await _collect(deps)
    assert any(isinstance(f, dict) and f["kind"] == "error" for f in frames)
    assert frames[-1] == "[DONE]", "the client must always see the stream close"
