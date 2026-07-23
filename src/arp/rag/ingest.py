"""Corpus ingestion: catalogue → embeddings → vector store.

Run via `make ingest` (equivalently `python -m arp.rag.ingest`).
"""

import json
from pathlib import Path

from arp.config import get_settings
from arp.llm.provider import LLMProvider, get_provider
from arp.models import CatalogueItem
from arp.rag.store import VectorStore

CATALOGUE_PATH = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "catalogue.json"


def load_catalogue(path: Path | None = None) -> list[CatalogueItem]:
    raw = json.loads(Path(path or CATALOGUE_PATH).read_text(encoding="utf-8"))
    return [CatalogueItem.model_validate(entry) for entry in raw]


def to_document(item: CatalogueItem) -> str:
    """Flatten a sheet into the text that gets embedded.

    Specs are folded in so retrieval keys on material and attributes, not the
    title alone — that is what makes a sparse sheet findable.
    """
    parts = [item.title]
    if item.category:
        parts.append(f"catégorie: {item.category}")
    parts.extend(f"{key}: {value}" for key, value in sorted(item.specs.items()))
    return " | ".join(parts)


def ingest(provider: LLMProvider, store: VectorStore, items: list[CatalogueItem]) -> int:
    documents = [to_document(item) for item in items]
    embeddings = provider.embed(documents)
    for item, document, embedding in zip(items, documents, embeddings, strict=True):
        store.upsert(
            id=item.id,
            text=document,
            embedding=embedding,
            metadata={"title": item.title, "category": item.category, "specs": item.specs},
        )
    return len(items)


def main() -> None:
    from arp.rag.store import PgVectorStore

    settings = get_settings()
    items = load_catalogue()
    store = PgVectorStore(settings.database_url, dim=settings.embed_dim)
    count = ingest(get_provider(settings), store, items)
    print(f"ingested {count} catalogue items into {settings.database_url}")


if __name__ == "__main__":
    main()
