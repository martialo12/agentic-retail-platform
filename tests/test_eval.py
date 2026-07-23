import pytest

from arp.agents.product_enricher.schema import EnrichedProduct
from arp.llmops.eval import EvalReport, GoldenItem, load_golden, run_eval, to_markdown

GOLDEN = [
    GoldenItem(
        sheet={"id": "p1", "title": "Chaise en chêne", "specs": {}},
        reference={"category": "mobilier", "materials": ["chêne massif"]},
    ),
    GoldenItem(
        sheet={"id": "p2", "title": "Lampe LED", "specs": {}},
        reference={"category": "luminaire", "materials": ["aluminium"]},
    ),
    GoldenItem(
        sheet={"id": "p3", "title": "Plaid en laine", "specs": {}},
        reference={"category": "textile", "materials": ["laine mérinos"]},
    ),
]


def _emitted(category, materials):
    return {
        "output": EnrichedProduct(
            category=category,
            materials=materials,
            use_cases=["x"],
            seo_description="d",
            confidence=0.9,
        ),
        "escalated": False,
    }


ESCALATED = {"output": None, "escalated": True}


async def test_report_populates_every_metric():
    async def runner(sheet):
        return _emitted("mobilier", ["chêne massif"])

    report = await run_eval(runner, GOLDEN)
    assert isinstance(report, EvalReport)
    assert report.items == 3
    assert report.field_coverage is not None
    assert report.exact_match is not None
    assert report.escalation_rate is not None


async def test_perfect_agent_scores_one():
    async def runner(sheet):
        item = next(g for g in GOLDEN if g.sheet["id"] == sheet["id"])
        return _emitted(item.reference["category"], item.reference["materials"])

    report = await run_eval(runner, GOLDEN)
    assert report.exact_match == 1.0
    assert report.field_coverage == 1.0
    assert report.escalation_rate == 0.0


async def test_wrong_agent_scores_zero_exact_match():
    async def runner(sheet):
        return _emitted("faux", ["faux"])

    report = await run_eval(runner, GOLDEN)
    assert report.exact_match == 0.0
    assert report.field_coverage == 1.0, "wrong but populated still counts as covered"


async def test_escalation_rate_counts_escalated_runs():
    async def runner(sheet):
        return ESCALATED if sheet["id"] == "p1" else _emitted("mobilier", ["chêne massif"])

    report = await run_eval(runner, GOLDEN)
    assert report.escalation_rate == pytest.approx(1 / 3)


async def test_escalated_items_are_excluded_from_quality_metrics():
    """An escalated run produced no output; scoring it as wrong would punish
    the very behaviour the socle is designed to encourage."""

    async def runner(sheet):
        return ESCALATED

    report = await run_eval(runner, GOLDEN)
    assert report.escalation_rate == 1.0
    assert report.scored_items == 0
    assert report.exact_match == 0.0


async def test_report_renders_markdown():
    async def runner(sheet):
        return _emitted("mobilier", ["chêne massif"])

    md = to_markdown(await run_eval(runner, GOLDEN))
    assert "field coverage" in md.lower()
    assert "escalation" in md.lower()


def test_golden_set_loads_from_disk():
    golden = load_golden()
    assert len(golden) >= 3
    assert all(g.sheet.get("id") and g.reference for g in golden)


def test_golden_sheets_are_incomplete_by_construction():
    """The golden set exists to measure enrichment, so its sheets must lack specs."""
    assert all(not g.sheet.get("specs") for g in load_golden())
