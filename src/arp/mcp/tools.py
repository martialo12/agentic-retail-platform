"""Business capabilities exposed over MCP (FR-003).

Pure functions over an injected `Repository`: no globals, no I/O of their own,
so each is unit-testable in isolation and trivially wrappable by the MCP server.
"""

import unicodedata

from arp.mcp.repository import Repository
from arp.models import CatalogueItem, Order


def _normalize(text: str) -> str:
    """Fold case and accents so 'CHENE' matches 'chêne' in the French catalogue."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def get_product(repo: Repository, product_id: str) -> CatalogueItem:
    item = repo.get_product(product_id)
    if item is None:
        raise KeyError(f"unknown product '{product_id}'")
    return item


def lookup_order(repo: Repository, order_id: str) -> Order:
    order = repo.get_order(order_id)
    if order is None:
        raise KeyError(f"unknown order '{order_id}'")
    return order


def search_catalog(repo: Repository, query: str, k: int = 5) -> list[CatalogueItem]:
    """Keyword search over titles and specs.

    Deliberately lexical: semantic retrieval is the RAG layer's job (FR-006),
    and keeping them separate lets an agent use either without the other.
    """
    needle = _normalize(query)
    hits = [
        item
        for item in repo.list_products()
        if needle in _normalize(item.title)
        or any(needle in _normalize(v) for v in item.specs.values())
    ]
    return hits[:k]


def write_enrichment(repo: Repository, product_id: str, attributes: dict) -> None:
    """The only mutating tool — hence the one gated most tightly by policy."""
    if repo.get_product(product_id) is None:
        raise KeyError(f"unknown product '{product_id}'")
    repo.save_enrichment(product_id, attributes)
