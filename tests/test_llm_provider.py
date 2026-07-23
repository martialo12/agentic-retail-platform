import pytest
from pydantic import BaseModel, Field

from arp.config import Settings
from arp.llm.provider import FakeProvider, LLMProvider, LocalProvider, VertexProvider, get_provider


class Reply(BaseModel):
    answer: str
    score: float = Field(ge=0.0, le=1.0)
    tags: list[str]
    ok: bool


MESSAGES = [{"role": "user", "content": "enrich this sheet"}]


def test_fake_complete_returns_valid_schema_instance():
    out = FakeProvider().complete(MESSAGES, Reply)
    assert isinstance(out, Reply)
    assert 0.0 <= out.score <= 1.0


def test_fake_complete_is_deterministic():
    a = FakeProvider().complete(MESSAGES, Reply)
    b = FakeProvider().complete(MESSAGES, Reply)
    assert a == b


def test_fake_complete_varies_with_input():
    other = [{"role": "user", "content": "a different question"}]
    assert FakeProvider().complete(MESSAGES, Reply) != FakeProvider().complete(other, Reply)


def test_fake_complete_respects_scripted_output():
    scripted = Reply(answer="scripted", score=0.9, tags=["x"], ok=True)
    assert FakeProvider(responses=[scripted]).complete(MESSAGES, Reply) == scripted


def test_fake_embed_is_deterministic_and_fixed_width():
    vecs = FakeProvider().embed(["alpha", "beta"])
    assert len(vecs) == 2
    assert len({len(v) for v in vecs}) == 1
    assert vecs == FakeProvider().embed(["alpha", "beta"])
    assert vecs[0] != vecs[1]


def test_fake_provider_satisfies_protocol():
    assert isinstance(FakeProvider(), LLMProvider)


@pytest.mark.parametrize(
    ("configured", "expected"),
    [("fake", FakeProvider), ("vertex", VertexProvider), ("local", LocalProvider)],
)
def test_get_provider_selects_by_settings(configured, expected):
    provider = get_provider(Settings(llm_provider=configured))
    assert isinstance(provider, expected)


def test_get_provider_does_not_open_connections():
    """Selection must stay lazy: constructing a provider must not need credentials."""
    assert isinstance(
        get_provider(Settings(llm_provider="vertex", vertex_project="")), VertexProvider
    )


class Inner(BaseModel):
    label: str
    weight: float


class Outer(BaseModel):
    title: str
    inner: Inner
    many: list[Inner]


def test_fake_complete_handles_nested_models():
    out = FakeProvider().complete(MESSAGES, Outer)
    assert isinstance(out, Outer)
    assert isinstance(out.inner, Inner)
    assert all(isinstance(i, Inner) for i in out.many)
