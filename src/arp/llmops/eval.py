"""Evaluation harness over the synthetic golden set (FR-012).

Run via `make eval` (equivalently `python -m arp.llmops.eval`).

Three metrics, chosen because they answer three different questions:
  - field coverage   — did the agent produce an answer at all?
  - exact match      — was that answer right?
  - escalation rate  — how often did it correctly decline to answer?

They are reported separately on purpose. An agent that escalates everything scores
a perfect zero on errors, which is why coverage and escalation must be read together.
"""

import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from pydantic import BaseModel, Field

GOLDEN_PATH = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "golden.json"
REPORT_PATH = Path("docs/eval/report.md")

Runner = Callable[[dict], Awaitable[dict]]


class GoldenItem(BaseModel):
    sheet: dict
    reference: dict


class ItemResult(BaseModel):
    id: str
    escalated: bool
    matched_fields: int = 0
    populated_fields: int = 0
    reference_fields: int = 0


class EvalReport(BaseModel):
    items: int
    scored_items: int
    field_coverage: float
    exact_match: float
    escalation_rate: float
    details: list[ItemResult] = Field(default_factory=list)


def load_golden(path: Path | None = None) -> list[GoldenItem]:
    raw = json.loads(Path(path or GOLDEN_PATH).read_text(encoding="utf-8"))
    return [GoldenItem.model_validate(entry) for entry in raw]


def _normalize(value: object) -> object:
    if isinstance(value, list):
        return sorted(str(v).strip().casefold() for v in value)
    return str(value).strip().casefold()


async def run_eval(runner: Runner, golden: list[GoldenItem]) -> EvalReport:
    details: list[ItemResult] = []

    for item in golden:
        state = await runner(item.sheet)
        escalated = bool(state.get("escalated"))
        output = state.get("output")
        result = ItemResult(
            id=item.sheet.get("id", "?"),
            escalated=escalated,
            reference_fields=len(item.reference),
        )
        if not escalated and output is not None:
            produced = output.model_dump() if hasattr(output, "model_dump") else dict(output)
            for field, expected in item.reference.items():
                actual = produced.get(field)
                if actual not in (None, "", [], {}):
                    result.populated_fields += 1
                if actual is not None and _normalize(actual) == _normalize(expected):
                    result.matched_fields += 1
        details.append(result)

    scored = [d for d in details if not d.escalated]
    total_ref = sum(d.reference_fields for d in scored)
    return EvalReport(
        items=len(details),
        scored_items=len(scored),
        field_coverage=(sum(d.populated_fields for d in scored) / total_ref) if total_ref else 0.0,
        exact_match=(sum(d.matched_fields for d in scored) / total_ref) if total_ref else 0.0,
        escalation_rate=(sum(d.escalated for d in details) / len(details)) if details else 0.0,
        details=details,
    )


def to_markdown(report: EvalReport) -> str:
    pct = lambda v: f"{v * 100:.1f}%"  # noqa: E731
    lines = [
        "# Evaluation report — product-enricher",
        "",
        f"Golden set: **{report.items}** sheets, **{report.scored_items}** scored "
        f"({report.items - report.scored_items} escalated to a human).",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Field coverage | {pct(report.field_coverage)} |",
        f"| Exact match vs reference | {pct(report.exact_match)} |",
        f"| Escalation rate | {pct(report.escalation_rate)} |",
        "",
        "Quality metrics are computed over non-escalated runs only: an escalated run",
        "produced no output, and scoring it as wrong would penalise exactly the",
        "behaviour the socle is built to encourage.",
        "",
        "## Per-item",
        "",
        "| Sheet | Outcome | Matched / reference fields |",
        "|---|---|---|",
    ]
    for d in report.details:
        outcome = "escalated" if d.escalated else "emitted"
        lines.append(f"| {d.id} | {outcome} | {d.matched_fields} / {d.reference_fields} |")
    return "\n".join(lines) + "\n"


async def _main() -> None:
    from arp.agents import AGENTS_DIR
    from arp.agents.product_enricher.graph import build_enricher
    from arp.config import get_settings
    from arp.llm.provider import get_provider
    from arp.llmops.tracing import trace_run
    from arp.mcp.client import ToolClient
    from arp.mcp.repository import InMemoryRepository
    from arp.mcp.server import build_server
    from arp.rag.ingest import ingest, load_catalogue
    from arp.rag.retriever import Retriever
    from arp.rag.store import InMemoryVectorStore
    from arp.registry import load_agent

    settings = get_settings()
    provider = get_provider(settings)
    items = load_catalogue()
    store = InMemoryVectorStore()
    ingest(provider, store, items)
    retriever = Retriever(store, provider)
    repo = InMemoryRepository(items=items)
    spec = load_agent("product-enricher", AGENTS_DIR)

    async def runner(sheet: dict) -> dict:
        with trace_run(spec.id, provider=settings.llm_provider) as tracer:
            client = ToolClient(build_server(repo), spec, tracer)
            graph = build_enricher(spec, provider, retriever, client, tracer)
            return await graph.ainvoke({"sheet": sheet})

    report = await run_eval(runner, load_golden())
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(to_markdown(report), encoding="utf-8")
    print(
        f"coverage={report.field_coverage:.1%} "
        f"exact_match={report.exact_match:.1%} "
        f"escalation={report.escalation_rate:.1%} → {REPORT_PATH}"
    )


def main() -> None:
    import asyncio

    asyncio.run(_main())


if __name__ == "__main__":
    main()
