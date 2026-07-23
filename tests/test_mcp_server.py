import json

import pytest

from arp.mcp.repository import InMemoryRepository
from arp.mcp.server import build_server
from arp.mcp.tools import get_product
from arp.models import CatalogueItem, Order
from arp.tools import TOOL_CATALOG

ITEMS = [
    CatalogueItem(
        id="p1", title="Chaise en chêne", specs={"matiere": "chêne"}, category="mobilier"
    ),
    CatalogueItem(id="p2", title="Table basse", specs={}, category="mobilier"),
]
ORDERS = [Order(id="o1", status="shipped", product_ids=["p1"], customer_ref="c-001")]


@pytest.fixture
def repo():
    return InMemoryRepository(items=list(ITEMS), orders=list(ORDERS))


@pytest.fixture
def server(repo):
    return build_server(repo)


async def test_server_exposes_exactly_the_catalogue(server):
    """FR-003: the MCP surface is the tool catalogue, no more and no less."""
    names = {tool.name for tool in await server.list_tools()}
    assert names == set(TOOL_CATALOG)


async def test_every_exposed_tool_is_described(server):
    assert all(tool.description for tool in await server.list_tools())


async def test_get_product_over_mcp_matches_direct_call(server, repo):
    result = await server.call_tool("get_product", {"product_id": "p1"})
    assert _payload(result)["title"] == get_product(repo, "p1").title


async def test_search_catalog_over_mcp(server):
    result = await server.call_tool("search_catalog", {"query": "table", "k": 5})
    assert [hit["id"] for hit in _payload(result)["items"]] == ["p2"]


async def test_lookup_order_over_mcp(server):
    result = await server.call_tool("lookup_order", {"order_id": "o1"})
    assert _payload(result)["status"] == "shipped"


async def test_write_enrichment_over_mcp_persists(server, repo):
    await server.call_tool(
        "write_enrichment", {"product_id": "p2", "attributes": {"category": "x"}}
    )
    assert repo.get_enrichment("p2") == {"category": "x"}


async def test_unknown_product_surfaces_as_error(server):
    with pytest.raises(Exception):  # noqa: B017 - MCP wraps tool errors in its own type
        await server.call_tool("get_product", {"product_id": "nope"})


def _payload(result):
    """FastMCP returns a list of content blocks; the tool's JSON sits in the first."""
    return json.loads(result[0].text)
