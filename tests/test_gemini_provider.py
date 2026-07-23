"""The Gemini Developer API provider: API key instead of gcloud ADC.

Everything here is offline — the HTTP boundary is stubbed. A live call is a
demo concern, not a test concern.
"""

import pytest
from pydantic import BaseModel, Field

from arp.config import Settings
from arp.llm.provider import GeminiProvider, get_provider
from arp.llm.provider import _contents as contents
from arp.llm.provider import _response_schema as response_schema


class Reply(BaseModel):
    answer: str
    tags: list[str] = Field(default_factory=list)
    escalate: bool = False


class Nested(BaseModel):
    reply: Reply
    score: float


@pytest.fixture
def settings():
    # Model pinned explicitly: these tests cover routing, not the configured default.
    return Settings(llm_provider="gemini", gemini_api_key="k", gemini_model="gemini-x", embed_dim=4)


def test_provider_selection_is_config_driven(settings):
    assert isinstance(get_provider(settings), GeminiProvider)


def test_response_schema_drops_keys_gemini_rejects():
    """Gemini accepts an OpenAPI subset; `title`/`default` make it 400."""
    schema = response_schema(Reply)
    assert "title" not in schema
    assert all(
        "title" not in prop and "default" not in prop for prop in schema["properties"].values()
    )


def test_response_schema_keeps_the_shape():
    schema = response_schema(Reply)
    assert schema["type"] == "object"
    assert schema["properties"]["answer"]["type"] == "string"
    assert schema["properties"]["tags"]["items"]["type"] == "string"
    assert schema["properties"]["escalate"]["type"] == "boolean"
    assert schema["required"] == ["answer"]


def test_response_schema_inlines_nested_models():
    """Pydantic emits $ref/$defs; Gemini understands neither."""
    schema = response_schema(Nested)
    assert "$defs" not in schema
    inlined = schema["properties"]["reply"]
    assert inlined["type"] == "object"
    assert inlined["properties"]["answer"]["type"] == "string"


def test_contents_splits_system_instruction_from_turns():
    """Gemini carries the system prompt out-of-band, not as a turn."""
    system, turns = contents(
        [
            {"role": "system", "content": "tu es un assistant"},
            {"role": "user", "content": "bonjour"},
            {"role": "assistant", "content": "salut"},
        ]
    )
    assert system == "tu es un assistant"
    assert turns == [
        {"role": "user", "parts": [{"text": "bonjour"}]},
        # OpenAI says "assistant", Gemini says "model".
        {"role": "model", "parts": [{"text": "salut"}]},
    ]


def test_complete_posts_to_gemini_and_validates(settings, monkeypatch):
    seen = {}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen["headers"] = kwargs["headers"]
        seen["json"] = kwargs["json"]
        return _Response({"candidates": [{"content": {"parts": [{"text": '{"answer":"ok"}'}]}}]})

    monkeypatch.setattr("httpx.post", fake_post)
    result = GeminiProvider(settings).complete([{"role": "user", "content": "salut"}], Reply)

    assert result == Reply(answer="ok")
    assert seen["url"].endswith("/models/gemini-x:generateContent")
    assert seen["headers"]["x-goog-api-key"] == "k"
    assert seen["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_complete_rejects_output_that_breaks_the_schema(settings, monkeypatch):
    """A bad payload must raise so the bounded retry sees it (FR-008)."""
    monkeypatch.setattr(
        "httpx.post",
        lambda url, **kw: _Response({"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}),
    )
    with pytest.raises(ValueError):
        GeminiProvider(settings).complete([{"role": "user", "content": "x"}], Reply)


def test_embed_requests_the_configured_width_and_normalises(settings, monkeypatch):
    """Truncated Matryoshka vectors are no longer unit-norm; cosine search needs them to be."""
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return _Response({"embeddings": [{"values": [3.0, 4.0, 0.0, 0.0]}]})

    monkeypatch.setattr("httpx.post", fake_post)
    (vector,) = GeminiProvider(settings).embed(["chaise"])

    assert captured["url"].endswith("/models/gemini-embedding-2:batchEmbedContents")
    assert captured["json"]["requests"][0]["outputDimensionality"] == 4
    assert vector == pytest.approx([0.6, 0.8, 0.0, 0.0])


def test_embed_sends_one_request_per_text(settings, monkeypatch):
    monkeypatch.setattr(
        "httpx.post",
        lambda url, **kw: _Response({"embeddings": [{"values": [1.0, 0.0, 0.0, 0.0]}] * 3}),
    )
    assert len(GeminiProvider(settings).embed(["a", "b", "c"])) == 3


def test_transient_disconnect_is_retried(settings, monkeypatch):
    """Observed in practice: the endpoint drops the connection under load."""
    import httpx

    calls = []

    def flaky(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        return _Response({"candidates": [{"content": {"parts": [{"text": '{"answer":"ok"}'}]}}]})

    monkeypatch.setattr("httpx.post", flaky)
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert (
        GeminiProvider(settings).complete([{"role": "user", "content": "x"}], Reply).answer == "ok"
    )
    assert len(calls) == 2


def test_overloaded_model_is_retried(settings, monkeypatch):
    """503 UNAVAILABLE means 'try again', unlike 400 or 429."""

    calls = []

    def overloaded(url, **kwargs):
        calls.append(url)
        if len(calls) < 3:
            return _Response({}, status=503)
        return _Response({"candidates": [{"content": {"parts": [{"text": '{"answer":"ok"}'}]}}]})

    monkeypatch.setattr("httpx.post", overloaded)
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert (
        GeminiProvider(settings).complete([{"role": "user", "content": "x"}], Reply).answer == "ok"
    )
    assert len(calls) == 3


def test_retries_are_bounded(settings, monkeypatch):
    """Never retry forever: a persistently dead endpoint must surface as an error."""
    import httpx

    calls = []

    def always_down(url, **kwargs):
        calls.append(url)
        raise httpx.ConnectError("nope")

    monkeypatch.setattr("httpx.post", always_down)
    monkeypatch.setattr("time.sleep", lambda _: None)

    with pytest.raises(httpx.ConnectError):
        GeminiProvider(settings).complete([{"role": "user", "content": "x"}], Reply)
    assert len(calls) == 3


def test_client_errors_are_not_retried(settings, monkeypatch):
    """A 400 is our bug; retrying it just burns quota."""
    import httpx

    calls = []

    def bad_request(url, **kwargs):
        calls.append(url)
        return _Response({"error": {"code": 400}}, status=400)

    monkeypatch.setattr("httpx.post", bad_request)
    monkeypatch.setattr("time.sleep", lambda _: None)

    with pytest.raises(httpx.HTTPStatusError):
        GeminiProvider(settings).complete([{"role": "user", "content": "x"}], Reply)
    assert len(calls) == 1


def test_missing_api_key_fails_loudly(monkeypatch):
    provider = GeminiProvider(Settings(llm_provider="gemini", gemini_api_key=""))
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        provider.complete([{"role": "user", "content": "x"}], Reply)


class _Response:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        import httpx

        if self.status_code >= 400:
            raise httpx.HTTPStatusError(f"{self.status_code}", request=None, response=self)

    def json(self) -> dict:
        return self._payload
