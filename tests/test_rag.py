import os

import pytest

from arp.llm.provider import EMBED_DIM, FakeProvider
from arp.models import CatalogueItem
from arp.rag.ingest import ingest, load_catalogue
from arp.rag.retriever import Retriever
from arp.rag.store import Hit, InMemoryVectorStore

ITEMS = [
    CatalogueItem(
        id="p1", title="Chaise en chêne massif", specs={"coloris": "naturel"}, category="mobilier"
    ),
    CatalogueItem(
        id="p2", title="Lampe de bureau LED", specs={"puissance": "9 W"}, category="luminaire"
    ),
    CatalogueItem(id="p3", title="Plaid en laine mérinos", specs={}, category=None),
]


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def store():
    return InMemoryVectorStore()


def test_ingest_upserts_every_item(store, provider):
    assert ingest(provider, store, ITEMS) == 3
    assert len(store) == 3


def test_ingest_is_idempotent(store, provider):
    ingest(provider, store, ITEMS)
    ingest(provider, store, ITEMS)
    assert len(store) == 3


def test_retriever_finds_the_seeded_product(store, provider):
    ingest(provider, store, ITEMS)
    hits = Retriever(store, provider).search("Chaise en chêne massif", k=2)
    assert hits[0].id == "p1"
    assert isinstance(hits[0], Hit)


def test_retriever_respects_k(store, provider):
    ingest(provider, store, ITEMS)
    assert len(Retriever(store, provider).search("Chaise en chêne massif", k=2)) == 2


def test_retriever_returns_empty_on_empty_store(store, provider):
    assert Retriever(store, provider).search("anything", k=3) == []


def test_hits_carry_metadata(store, provider):
    ingest(provider, store, ITEMS)
    hit = Retriever(store, provider).search("Lampe de bureau LED", k=1)[0]
    assert hit.metadata["category"] == "luminaire"


def test_hits_are_ordered_by_descending_score(store, provider):
    ingest(provider, store, ITEMS)
    scores = [h.score for h in Retriever(store, provider).search("Chaise en chêne massif", k=3)]
    assert scores == sorted(scores, reverse=True)


def test_embeddings_have_the_declared_width(provider):
    assert len(provider.embed(["x"])[0]) == EMBED_DIM


def test_load_catalogue_reads_the_synthetic_corpus():
    items = load_catalogue()
    assert len(items) >= 10
    assert all(isinstance(i, CatalogueItem) for i in items)
    assert any(not i.specs for i in items), "corpus must contain incomplete sheets to enrich"


# --- integration: real pgvector, skipped when the local stack is down -----------


def _pg_reachable() -> bool:
    try:
        import psycopg

        with psycopg.connect(os.environ.get("DATABASE_URL", DSN), connect_timeout=2):
            return True
    except Exception:
        return False


DSN = "postgresql://arp:arp@localhost:5432/arp"
pg = pytest.mark.skipif(not _pg_reachable(), reason="local postgres/pgvector not reachable")


@pg
def test_pgvector_roundtrip(provider):
    from arp.rag.store import PgVectorStore

    store = PgVectorStore(os.environ.get("DATABASE_URL", DSN), table="test_documents")
    store.reset()
    ingest(provider, store, ITEMS)
    hits = Retriever(store, provider).search("Chaise en chêne massif", k=2)
    assert hits[0].id == "p1"
    assert hits[0].metadata["category"] == "mobilier"
    assert len(hits) == 2


@pg
def test_pgvector_upsert_does_not_duplicate(provider):
    from arp.rag.store import PgVectorStore

    store = PgVectorStore(os.environ.get("DATABASE_URL", DSN), table="test_documents")
    store.reset()
    ingest(provider, store, ITEMS)
    ingest(provider, store, ITEMS)
    assert len(store) == 3


@pg
def test_pgvector_adapts_to_the_embedding_width(provider):
    """No hardcoded 768: the column is created from the width the model actually emits."""
    from arp.rag.store import PgVectorStore

    store = PgVectorStore(os.environ.get("DATABASE_URL", DSN), table="test_dim_probe")
    store.drop()
    store.upsert("a", "text", [0.1] * 16, {})
    assert store.dimension() == 16


@pg
def test_pgvector_rejects_a_width_mismatch(provider):
    """A model swap that changes width must fail loudly, not corrupt the index."""
    from arp.rag.store import PgVectorStore

    store = PgVectorStore(os.environ.get("DATABASE_URL", DSN), table="test_dim_probe")
    store.drop()
    store.upsert("a", "text", [0.1] * 16, {})
    with pytest.raises(ValueError, match="dimension"):
        store.upsert("b", "text", [0.1] * 32, {})


@pg
def test_pgvector_honours_an_explicit_dimension(provider):
    from arp.rag.store import PgVectorStore

    store = PgVectorStore(os.environ.get("DATABASE_URL", DSN), table="test_dim_fixed", dim=24)
    store.drop()
    store.upsert("a", "text", [0.1] * 24, {})
    assert store.dimension() == 24


def test_fake_provider_width_is_configurable():
    from arp.llm.provider import FakeProvider as FP

    assert len(FP(dim=128).embed(["x"])[0]) == 128
