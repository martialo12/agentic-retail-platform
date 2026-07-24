"""The HTTP surface. Deliberately unauthenticated (FR-018)."""

import pytest
from httpx import ASGITransport, AsyncClient

from arp.api.routes import create_app
from arp.api.wiring import build_deps
from arp.config import Settings
from arp.llmops.run_store import InMemoryRunStore


@pytest.fixture
def deps():
    return build_deps(Settings(llm_provider="fake"), run_store=InMemoryRunStore())


@pytest.fixture
def client(deps):
    return AsyncClient(transport=ASGITransport(app=create_app(deps)), base_url="http://test")


async def _drain(client, question="Où en est ma commande o001 ?") -> str:
    async with client.stream("POST", "/api/assistant/ask", json={"question": question}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        return "".join([chunk async for chunk in response.aiter_text()])


async def test_health_is_cheap(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_catalogue_lists_the_synthetic_sheets(client):
    response = await client.get("/api/catalogue")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 20


async def test_ask_streams_events(client):
    body = await _drain(client)
    assert "data: [DONE]" in body
    assert '"kind": "tool_call"' in body


async def test_a_sensitive_intent_streams_an_escalation(client):
    """SC-007: the refusal and its reason must reach the browser."""
    body = await _drain(client, "Je veux un remboursement pour o001")
    assert '"kind": "escalation"' in body
    assert "remboursement" in body


async def test_runs_are_listed_and_detailed_after_a_run(client):
    await _drain(client)
    listed = (await client.get("/api/runs")).json()
    assert listed["total"] >= 1
    detail = (await client.get(f"/api/runs/{listed['items'][0]['run_id']}")).json()
    assert detail["agent_id"] == "customer-assistant"
    assert detail["events"]


async def test_runs_can_be_filtered(client):
    await _drain(client)
    assert (await client.get("/api/runs?agent=product-enricher")).json()["total"] == 0


async def test_an_unknown_run_is_404(client):
    assert (await client.get("/api/runs/nope")).status_code == 404


async def test_an_unknown_product_is_404(client):
    response = await client.post("/api/enricher/enrich", json={"product_id": "p999"})
    assert response.status_code == 404


async def test_a_blank_question_is_rejected(client):
    assert (await client.post("/api/assistant/ask", json={"question": "   "})).status_code == 422


async def test_a_missing_question_is_rejected(client):
    assert (await client.post("/api/assistant/ask", json={})).status_code == 422
