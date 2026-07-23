"""Generate the synthetic order book (FR-013: no real customer data, ever).

Deterministic by construction — no RNG — like the catalogue generator, so the
corpus stays stable across runs and the evaluation harness is reproducible.

Orders reference real catalogue ids, so `lookup_order` and `get_product` compose:
the assistant can look up a commande and then describe what is in it.

Usage: uv run python scripts/gen_orders.py
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "synthetic"
CATALOGUE = DATA_DIR / "catalogue.json"
OUT = DATA_DIR / "orders.json"

# Statuses a customer actually asks about, in the assistant's language.
STATUSES = [
    "en préparation",
    "expédiée",
    "livrée",
    "en attente de paiement",
    "annulée",
    "retour en cours",
]

# Two orders per status, so every branch of the demo has a spare.
ORDER_COUNT = len(STATUSES) * 2
CUSTOMER_COUNT = 5


def build(catalogue_path: Path | None = None) -> list[dict]:
    products = [
        item["id"]
        for item in json.loads(Path(catalogue_path or CATALOGUE).read_text(encoding="utf-8"))
    ]

    orders = []
    for index in range(1, ORDER_COUNT + 1):
        # Walk the catalogue with a stride so successive orders hold different
        # items rather than all pointing at the first few products.
        size = (index % 3) + 1
        start = ((index - 1) * 2) % len(products)
        orders.append(
            {
                "id": f"o{index:03d}",
                "status": STATUSES[(index - 1) % len(STATUSES)],
                "product_ids": [
                    products[(start + offset) % len(products)] for offset in range(size)
                ],
                # Pseudonymous by design: an order carries a reference, never a person.
                "customer_ref": f"c-{((index - 1) % CUSTOMER_COUNT) + 1:03d}",
            }
        )
    return orders


def main() -> None:
    orders = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(orders, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(orders)} orders to {OUT}")


if __name__ == "__main__":
    main()
