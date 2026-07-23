"""Ask an agent a question from the terminal.

The demo seam: everything the eval harness wires up, driven by hand instead of
by a golden set. Run via `make ask` / `make enrich`, or:

    python -m arp.cli ask "Où en est ma commande o002 ?"
    python -m arp.cli enrich p003
"""

import argparse
import asyncio
import json
import sys

from arp.agents import AGENTS_DIR
from arp.config import get_settings
from arp.llm.provider import get_provider
from arp.llmops.tracing import trace_run
from arp.mcp.client import ToolClient
from arp.mcp.repository import InMemoryRepository
from arp.mcp.server import build_server
from arp.registry import load_agent


def _repository() -> InMemoryRepository:
    from arp.mcp.__main__ import build_repository

    return build_repository()


async def _ask(question: str) -> dict:
    from arp.agents.customer_assistant.graph import build_assistant

    settings = get_settings()
    spec = load_agent("customer-assistant", AGENTS_DIR)
    with trace_run(spec.id, provider=settings.llm_provider) as tracer:
        client = ToolClient(build_server(_repository()), spec, tracer)
        graph = build_assistant(spec, get_provider(settings), client, tracer)
        return await graph.ainvoke({"question": question})


async def _enrich(product_id: str) -> dict:
    from arp.agents.product_enricher.graph import build_enricher
    from arp.rag.retriever import Retriever
    from arp.rag.store import PgVectorStore

    settings = get_settings()
    repo = _repository()
    sheet = repo.get_product(product_id)
    if sheet is None:
        raise SystemExit(f"unknown product '{product_id}' — try p003, p006, p009…")

    provider = get_provider(settings)
    spec = load_agent("product-enricher", AGENTS_DIR)
    with trace_run(spec.id, provider=settings.llm_provider) as tracer:
        client = ToolClient(build_server(repo), spec, tracer)
        retriever = Retriever(PgVectorStore(settings.database_url), provider)
        graph = build_enricher(spec, provider, retriever, client, tracer)
        return await graph.ainvoke({"sheet": sheet.model_dump()})


def _render(state: dict) -> None:
    """Show the decision, not just the text: escalation is the interesting outcome."""
    if state.get("escalated"):
        print("→ ESCALADE VERS UN HUMAIN")
        print(f"  raison: {state.get('reason') or 'non précisée'}")
    output = state.get("output")
    if output is not None:
        print(json.dumps(output.model_dump(), ensure_ascii=False, indent=2))
    if tools := state.get("tools_used"):
        print(f"\noutils MCP appelés: {', '.join(tools)}")
    print("trace: logs/runs/")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="arp", description="Interroger les agents en local.")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="poser une question au customer-assistant")
    ask.add_argument("question", nargs="+")

    enrich = sub.add_parser("enrich", help="enrichir une fiche avec le product-enricher")
    enrich.add_argument("product_id")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if args.command == "ask":
        _render(asyncio.run(_ask(" ".join(args.question))))
    else:
        _render(asyncio.run(_enrich(args.product_id)))


if __name__ == "__main__":
    main()
