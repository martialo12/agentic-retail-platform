import pytest
from pydantic import ValidationError

from arp.agents import AGENTS_DIR
from arp.agents.product_enricher.schema import EnrichedProduct
from arp.registry import load_agent

VALID = {
    "category": "mobilier",
    "materials": ["chêne massif"],
    "use_cases": ["salle à manger"],
    "seo_description": "Chaise en chêne massif pour salle à manger.",
    "confidence": 0.82,
}


def test_accepts_a_complete_draft():
    out = EnrichedProduct.model_validate(VALID)
    assert out.category == "mobilier"
    assert out.confidence == 0.82


@pytest.mark.parametrize("bad", [-0.1, 1.1, 2.0])
def test_rejects_confidence_outside_unit_interval(bad):
    with pytest.raises(ValidationError):
        EnrichedProduct.model_validate({**VALID, "confidence": bad})


def test_confidence_is_required():
    payload = {k: v for k, v in VALID.items() if k != "confidence"}
    with pytest.raises(ValidationError):
        EnrichedProduct.model_validate(payload)


def test_rejects_blank_seo_description():
    with pytest.raises(ValidationError):
        EnrichedProduct.model_validate({**VALID, "seo_description": "   "})


def test_lists_default_to_empty_not_none():
    payload = {k: v for k, v in VALID.items() if k not in ("materials", "use_cases")}
    out = EnrichedProduct.model_validate(payload)
    assert out.materials == [] and out.use_cases == []


def test_output_is_immutable():
    with pytest.raises(ValidationError):
        EnrichedProduct.model_validate(VALID).confidence = 0.1


# --- registry spec ---------------------------------------------------------


def test_spec_loads_from_the_registry():
    spec = load_agent("product-enricher", AGENTS_DIR)
    assert spec.id == "product-enricher"
    assert spec.owner


def test_spec_grants_exactly_the_enricher_tools():
    spec = load_agent("product-enricher", AGENTS_DIR)
    assert set(spec.allowed_tools) == {"search_catalog", "get_product", "write_enrichment"}


def test_spec_declares_an_escalation_threshold():
    spec = load_agent("product-enricher", AGENTS_DIR)
    assert 0.0 < spec.escalation.min_confidence <= 1.0
