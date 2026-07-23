"""Assemble the socle once, so the routes stay about HTTP.

This mirrors what `arp/cli.py` does — the CLI was effectively this API's
prototype. Keeping the assembly here means a route can never quietly bypass the
policy layer by building its own client.
"""

from dataclasses import dataclass
from typing import Any

from arp.agents import AGENTS_DIR
from arp.config import Settings, get_settings
from arp.llm.provider import LLMProvider, get_provider
from arp.llmops.run_store import InMemoryRunStore, PgRunStore, RunStore
from arp.llmops.tracing import RunTracer
from arp.mcp.__main__ import build_repository
from arp.mcp.client import ToolClient
from arp.mcp.repository import InMemoryRepository
from arp.mcp.server import build_server
from arp.registry import load_agent


@dataclass(frozen=True)
class Deps:
    settings: Settings
    repo: InMemoryRepository
    provider: LLMProvider
    run_store: RunStore


def build_deps(settings: Settings | None = None, run_store: RunStore | None = None) -> Deps:
    settings = settings or get_settings()
    if run_store is None:
        try:
            run_store = PgRunStore(settings.database_url)
        except Exception:  # noqa: BLE001
            # No database means a degraded observability view, not a dead API.
            # Runs still stream, and the JSONL audit record is still written.
            run_store = InMemoryRunStore()
    return Deps(
        settings=settings,
        repo=build_repository(),
        provider=get_provider(settings),
        run_store=run_store,
    )


def build_assistant_graph(deps: Deps, tracer: RunTracer) -> Any:
    from arp.agents.customer_assistant.graph import build_assistant

    spec = load_agent("customer-assistant", AGENTS_DIR)
    client = ToolClient(build_server(deps.repo), spec, tracer)
    return build_assistant(spec, deps.provider, client, tracer)


def build_enricher_graph(deps: Deps, tracer: RunTracer) -> Any:
    from arp.agents.product_enricher.graph import build_enricher
    from arp.rag.retriever import Retriever
    from arp.rag.store import PgVectorStore

    spec = load_agent("product-enricher", AGENTS_DIR)
    client = ToolClient(build_server(deps.repo), spec, tracer)
    retriever = Retriever(PgVectorStore(deps.settings.database_url), deps.provider)
    return build_enricher(spec, deps.provider, retriever, client, tracer)
