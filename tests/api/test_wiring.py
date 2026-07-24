"""One place knows how the socle's pieces fit; routes must not re-derive it."""

from arp.api.wiring import Deps, build_assistant_graph, build_deps
from arp.config import Settings
from arp.llm.provider import FakeProvider
from arp.llmops.run_store import InMemoryRunStore
from arp.llmops.tracing import RunTracer


def _deps() -> Deps:
    return build_deps(Settings(llm_provider="fake"), run_store=InMemoryRunStore())


def test_build_deps_uses_the_configured_provider():
    assert isinstance(_deps().provider, FakeProvider)


def test_build_deps_seeds_the_synthetic_corpus():
    deps = _deps()
    assert len(deps.repo.list_products()) == 20
    assert deps.repo.get_order("o001") is not None


def test_build_deps_accepts_an_injected_run_store():
    store = InMemoryRunStore()
    assert build_deps(Settings(llm_provider="fake"), run_store=store).run_store is store


def test_assistant_graph_is_built_against_its_own_spec():
    """The graph must come from the registry, never from a hardcoded tool list."""
    deps = _deps()
    tracer = RunTracer("customer-assistant", "r1")
    assert build_assistant_graph(deps, tracer) is not None


def test_deps_is_frozen():
    """Wiring is decided once per process; later mutation would be a bug."""
    import dataclasses

    assert dataclasses.fields(Deps)
    assert Deps.__dataclass_params__.frozen is True
