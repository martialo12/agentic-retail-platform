"""The single seam through which every model call passes.

Socle and agent code depends on `LLMProvider` only — never on a concrete vendor.
Swapping Vertex for a local endpoint is an env change, not a code change.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from arp.config import Settings, get_settings
from arp.text import tokenize

Message = dict[str, str]

EMBED_DIM = 768


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, messages: list[Message], schema: type[BaseModel]) -> BaseModel: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _seed(payload: str) -> int:
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


class FakeProvider:
    """Deterministic stand-in for tests: same input always yields the same output.

    Values are derived from a hash of the prompt, so tests can assert stability
    without pinning brittle literals. Pass `responses` to script exact returns.
    """

    def __init__(self, responses: list[BaseModel] | None = None, dim: int = EMBED_DIM) -> None:
        self._responses = list(responses or [])
        self._dim = dim

    def complete(self, messages: list[Message], schema: type[BaseModel]) -> BaseModel:
        if self._responses:
            return self._responses.pop(0)
        seed = _seed(json.dumps(messages, sort_keys=True) + schema.__name__)
        return schema.model_validate(
            {
                name: _fabricate(field.annotation, seed + i)
                for i, (name, field) in enumerate(schema.model_fields.items())
            }
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_embed(text, self._dim) for text in texts]


def _hash_embed(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic bag-of-words hashing vectorizer.

    Hashing whole strings would be deterministic but semantically blind: two
    near-identical sentences land in unrelated directions. Hashing *tokens* into
    dimensions gives crude lexical locality, so retrieval tests exercise real
    ranking behaviour instead of coincidence.
    """
    vector = [0.0] * dim
    for token in tokenize(text):
        bucket = _seed(token) % dim
        # Sign hashing keeps unrelated collisions from always reinforcing.
        vector[bucket] += 1.0 if _seed(token + "#sign") % 2 else -1.0
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def _fabricate(annotation: Any, seed: int) -> Any:
    """Build a deterministic value satisfying a field's type annotation."""
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        (inner,) = annotation.__args__
        return [_fabricate(inner, seed + n) for n in range(2)]
    if origin is dict:
        return {}
    if annotation is bool:
        return seed % 2 == 0
    if annotation is int:
        return seed % 100
    if annotation is float:
        # Kept within [0,1] so confidence-style fields validate.
        return (seed % 1000) / 1000.0
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return {
            name: _fabricate(field.annotation, seed + i)
            for i, (name, field) in enumerate(annotation.model_fields.items())
        }
    return f"fake-{seed % 10000}"


class VertexProvider:
    """Vertex AI Gemini. The client is built on first use so that selecting this
    provider never requires credentials (tests select without connecting)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._chat: Any = None
        self._embedder: Any = None

    def _get_chat(self) -> Any:
        if self._chat is None:
            from langchain_google_vertexai import ChatVertexAI

            self._chat = ChatVertexAI(
                model=self._settings.vertex_model,
                project=self._settings.vertex_project or None,
                location=self._settings.vertex_location,
            )
        return self._chat

    def _get_embedder(self) -> Any:
        if self._embedder is None:
            from langchain_google_vertexai import VertexAIEmbeddings

            self._embedder = VertexAIEmbeddings(
                model_name=self._settings.vertex_embed_model,
                project=self._settings.vertex_project or None,
                location=self._settings.vertex_location,
            )
        return self._embedder

    def complete(self, messages: list[Message], schema: type[BaseModel]) -> BaseModel:
        return self._get_chat().with_structured_output(schema).invoke(messages)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._get_embedder().embed_documents(texts)


class LocalProvider:
    """Any OpenAI-compatible endpoint (Ollama, vLLM, LM Studio).

    Talks HTTP directly rather than pulling in a vendor SDK: one less dependency,
    and it keeps the provider seam honest.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def complete(self, messages: list[Message], schema: type[BaseModel]) -> BaseModel:
        import httpx

        response = httpx.post(
            f"{self._settings.local_llm_base_url}/chat/completions",
            json={
                "model": self._settings.local_llm_model,
                "messages": messages,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
                },
            },
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return schema.model_validate_json(content)

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        response = httpx.post(
            f"{self._settings.local_llm_base_url}/embeddings",
            json={"model": self._settings.local_llm_model, "input": texts},
            timeout=120.0,
        )
        response.raise_for_status()
        return [item["embedding"] for item in response.json()["data"]]


GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_ATTEMPTS = 3
GEMINI_BACKOFF = 1.0
# 503 = model overloaded. Not 429: that is quota, and retrying makes it worse.
_RETRIABLE_STATUS = {503}

# Gemini's responseSchema is an OpenAPI 3.0 subset. Pydantic emits JSON Schema,
# which carries keys Gemini rejects outright with a 400.
_SCHEMA_KEYS = {"type", "properties", "required", "items", "enum", "description", "nullable"}


def _response_schema(schema: type[BaseModel]) -> dict:
    """Translate a Pydantic model into a schema Gemini will accept."""
    root = schema.model_json_schema()
    return _prune(root, root.get("$defs", {}))


def _prune(node: dict, defs: dict) -> dict:
    if ref := node.get("$ref"):
        node = {**defs[ref.rsplit("/", 1)[-1]], **{k: v for k, v in node.items() if k != "$ref"}}

    out = {key: value for key, value in node.items() if key in _SCHEMA_KEYS}
    if properties := node.get("properties"):
        out["properties"] = {name: _prune(sub, defs) for name, sub in properties.items()}
    if items := node.get("items"):
        out["items"] = _prune(items, defs)
    return out


def _contents(messages: list[Message]) -> tuple[str, list[dict]]:
    """Split the system prompt out: Gemini carries it out-of-band, not as a turn."""
    system = " ".join(m["content"] for m in messages if m["role"] == "system")
    turns = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]
    return system, turns


class GeminiProvider:
    """Gemini via the Developer API — an API key, no gcloud ADC.

    Talks HTTP directly for the same reason `LocalProvider` does: no vendor SDK,
    and the provider seam stays honest.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _key(self) -> str:
        if not self._settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is empty; set it in .env or the environment")
        return self._settings.gemini_api_key

    def _post(self, path: str, payload: dict) -> dict:
        """Retry only what retrying can fix.

        Under load the endpoint answers 503, or drops the connection outright.
        Both are transient. A 4xx is our own bug and retrying it only burns quota.
        """
        import time

        import httpx

        for attempt in range(1, GEMINI_ATTEMPTS + 1):
            last = attempt == GEMINI_ATTEMPTS
            try:
                response = httpx.post(
                    f"{GEMINI_API}/{path}",
                    headers={"x-goog-api-key": self._key(), "Content-Type": "application/json"},
                    json=payload,
                    timeout=120.0,
                )
                if response.status_code in _RETRIABLE_STATUS and not last:
                    time.sleep(GEMINI_BACKOFF * attempt)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.TransportError:
                if last:
                    raise
                time.sleep(GEMINI_BACKOFF * attempt)
        raise RuntimeError("unreachable")

    def complete(self, messages: list[Message], schema: type[BaseModel]) -> BaseModel:
        system, turns = _contents(messages)
        payload: dict[str, Any] = {
            "contents": turns,
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _response_schema(schema),
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        body = self._post(f"models/{self._settings.gemini_model}:generateContent", payload)
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        return schema.model_validate_json(text)

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = f"models/{self._settings.gemini_embed_model}"
        request: dict[str, Any] = {"model": model, "content": {}}
        if self._settings.embed_dim:
            request["outputDimensionality"] = self._settings.embed_dim

        body = self._post(
            f"{model}:batchEmbedContents",
            {"requests": [{**request, "content": {"parts": [{"text": text}]}} for text in texts]},
        )
        # Matryoshka truncation leaves vectors off the unit sphere; cosine
        # similarity in pgvector assumes they are on it.
        return [_normalise(item["values"]) for item in body["embeddings"]]


def _normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def get_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "fake":
        return FakeProvider(dim=settings.embed_dim or EMBED_DIM)
    if settings.llm_provider == "gemini":
        return GeminiProvider(settings)
    if settings.llm_provider == "local":
        return LocalProvider(settings)
    return VertexProvider(settings)
