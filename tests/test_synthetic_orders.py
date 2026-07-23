"""The synthetic order book the customer-assistant answers `lookup_order` from."""

import pytest

from arp.mcp.__main__ import build_repository
from arp.models import Order
from scripts.gen_orders import STATUSES, build


@pytest.fixture(scope="module")
def orders() -> list[Order]:
    return [Order.model_validate(entry) for entry in build()]


def test_generator_is_deterministic():
    """No RNG: the corpus must not drift between runs, or eval stops being reproducible."""
    assert build() == build()


def test_order_ids_match_the_reference_pattern(orders):
    """The assistant extracts order ids with `\\bo\\d+\\b`; ids must be findable."""
    import re

    pattern = re.compile(r"\bo\d+\b", re.IGNORECASE)
    assert all(pattern.fullmatch(order.id) for order in orders)


def test_orders_reference_real_catalogue_products(orders):
    known = {item.id for item in build_repository().list_products()}
    referenced = {pid for order in orders for pid in order.product_ids}
    assert referenced <= known
    assert referenced, "orders that reference nothing cannot exercise get_product"


def test_every_status_is_covered(orders):
    """Each status must appear at least once, so the demo can show every branch."""
    assert {order.status for order in orders} == set(STATUSES)


def test_orders_carry_a_synthetic_customer_reference(orders):
    """FR-013: pseudonymous references only, never anything resembling real identity."""
    assert all(order.customer_ref and order.customer_ref.startswith("c-") for order in orders)


def test_repository_seeds_orders_from_the_shipped_file():
    """The container answers lookup_order out of the box, with no extra setup."""
    repo = build_repository()
    assert repo.get_order("o001") is not None
