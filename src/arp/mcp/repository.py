"""Storage seam behind the business tools.

Tools depend on this protocol, never on a database, so unit tests run with no I/O.
"""

from typing import Protocol, runtime_checkable

from arp.models import CatalogueItem, Order


@runtime_checkable
class Repository(Protocol):
    def get_product(self, product_id: str) -> CatalogueItem | None: ...

    def list_products(self) -> list[CatalogueItem]: ...

    def get_order(self, order_id: str) -> Order | None: ...

    def save_enrichment(self, product_id: str, attributes: dict) -> None: ...

    def get_enrichment(self, product_id: str) -> dict | None: ...


class InMemoryRepository:
    """Reference implementation, and the one used by tests and the local demo."""

    def __init__(
        self,
        items: list[CatalogueItem] | None = None,
        orders: list[Order] | None = None,
    ) -> None:
        self._items = {item.id: item for item in items or []}
        self._orders = {order.id: order for order in orders or []}
        self._enrichments: dict[str, dict] = {}

    def get_product(self, product_id: str) -> CatalogueItem | None:
        return self._items.get(product_id)

    def list_products(self) -> list[CatalogueItem]:
        return list(self._items.values())

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def save_enrichment(self, product_id: str, attributes: dict) -> None:
        self._enrichments[product_id] = dict(attributes)

    def get_enrichment(self, product_id: str) -> dict | None:
        return self._enrichments.get(product_id)
