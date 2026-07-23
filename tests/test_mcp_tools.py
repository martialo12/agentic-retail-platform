import pytest

from arp.mcp.repository import InMemoryRepository
from arp.mcp.tools import get_product, lookup_order, search_catalog, write_enrichment
from arp.models import CatalogueItem, Order

ITEMS = [
    CatalogueItem(
        id="p1", title="Chaise en chêne massif", specs={"matiere": "chêne"}, category="mobilier"
    ),
    CatalogueItem(id="p2", title="Table basse en verre", specs={}, category="mobilier"),
    CatalogueItem(
        id="p3", title="Lampe de bureau LED", specs={"puissance": "9W"}, category="luminaire"
    ),
]
ORDERS = [Order(id="o1", status="shipped", product_ids=["p1"], customer_ref="c-001")]


@pytest.fixture
def repo():
    return InMemoryRepository(items=list(ITEMS), orders=list(ORDERS))


def test_get_product_returns_item(repo):
    assert get_product(repo, "p1").title == "Chaise en chêne massif"


def test_get_product_raises_on_unknown_id(repo):
    with pytest.raises(KeyError):
        get_product(repo, "nope")


def test_search_catalog_matches_on_title(repo):
    hits = search_catalog(repo, "table", k=5)
    assert [h.id for h in hits] == ["p2"]


def test_search_catalog_is_case_and_accent_insensitive(repo):
    assert [h.id for h in search_catalog(repo, "CHENE", k=5)] == ["p1"]


def test_search_catalog_respects_k(repo):
    assert len(search_catalog(repo, "e", k=2)) == 2


def test_search_catalog_returns_empty_on_no_match(repo):
    assert search_catalog(repo, "zzzz", k=5) == []


def test_lookup_order_returns_order(repo):
    assert lookup_order(repo, "o1").status == "shipped"


def test_lookup_order_raises_on_unknown_id(repo):
    with pytest.raises(KeyError):
        lookup_order(repo, "nope")


def test_write_enrichment_persists_and_is_readable(repo):
    write_enrichment(repo, "p2", {"category": "mobilier", "materials": ["verre"]})
    assert repo.get_enrichment("p2") == {"category": "mobilier", "materials": ["verre"]}


def test_write_enrichment_rejects_unknown_product(repo):
    with pytest.raises(KeyError):
        write_enrichment(repo, "nope", {"category": "x"})


def test_tools_do_not_mutate_the_catalogue(repo):
    write_enrichment(repo, "p1", {"category": "mobilier"})
    assert get_product(repo, "p1").title == "Chaise en chêne massif"
    assert get_product(repo, "p1").category == "mobilier"
