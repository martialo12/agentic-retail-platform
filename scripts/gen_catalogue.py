"""Generate the synthetic retail catalogue (FR-013: no real customer data, ever).

Deterministic by construction — no RNG — so the corpus and the golden set stay
stable across runs and the evaluation harness is reproducible.

Usage: uv run python scripts/gen_catalogue.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "catalogue.json"

CATEGORIES = {
    "mobilier": [
        (
            "Chaise de salle à manger en {matiere}",
            {"matiere": "chêne massif", "coloris": "naturel"},
        ),
        ("Table basse rectangulaire en {matiere}", {"matiere": "verre trempé"}),
        ("Étagère murale modulable en {matiere}", {"matiere": "pin", "charge_max": "15 kg"}),
        ("Fauteuil pivotant en {matiere}", {"matiere": "velours", "coloris": "bleu nuit"}),
        ("Buffet deux portes en {matiere}", {"matiere": "noyer"}),
    ],
    "luminaire": [
        ("Lampe de bureau articulée {matiere}", {"puissance": "9 W", "technologie": "LED"}),
        ("Suspension design en {matiere}", {"matiere": "laiton brossé"}),
        ("Applique murale {matiere}", {"matiere": "aluminium", "indice_protection": "IP44"}),
        ("Lampadaire trépied en {matiere}", {"matiere": "bois clair"}),
    ],
    "textile": [
        ("Coussin décoratif en {matiere}", {"matiere": "lin lavé", "dimensions": "45x45 cm"}),
        ("Plaid maille torsadée en {matiere}", {"matiere": "laine mérinos"}),
        ("Rideau occultant en {matiere}", {"matiere": "polyester recyclé"}),
        ("Tapis tissé main en {matiere}", {"matiere": "jute"}),
    ],
    "cuisine": [
        ("Poêle antiadhésive {matiere}", {"diametre": "28 cm", "compatible": "induction"}),
        ("Set de couteaux en {matiere}", {"matiere": "acier inoxydable", "pieces": "5"}),
        ("Planche à découper en {matiere}", {"matiere": "bambou"}),
        ("Casserole à fond épais en {matiere}", {"matiere": "inox 18/10"}),
    ],
    "rangement": [
        ("Boîte de rangement empilable en {matiere}", {"matiere": "polypropylène"}),
        ("Panier tressé en {matiere}", {"matiere": "rotin naturel"}),
        ("Casier à chaussures en {matiere}", {"matiere": "métal époxy"}),
    ],
}


def _title(template: str, specs: dict[str, str]) -> str:
    """Substitute the material when the entry declares one; drop the slot otherwise."""
    return " ".join(template.format(matiere=specs.get("matiere", "")).split())


def build() -> list[dict]:
    """Every third item ships with an empty spec map: those are the incomplete
    sheets the product-enricher exists to complete."""
    items = []
    index = 0
    for category, templates in CATEGORIES.items():
        for title_tpl, specs in templates:
            index += 1
            incomplete = index % 3 == 0
            items.append(
                {
                    "id": f"p{index:03d}",
                    "title": _title(title_tpl, specs),
                    "specs": {} if incomplete else specs,
                    "category": None if incomplete else category,
                }
            )
    return items


def main() -> None:
    items = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    incomplete = sum(1 for i in items if not i["specs"])
    print(f"wrote {len(items)} items ({incomplete} incomplete) to {OUT}")


if __name__ == "__main__":
    main()
