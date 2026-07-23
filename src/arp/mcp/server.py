"""The MCP server: the only door between an agent and business logic (FR-003).

Tools are registered as closures over an injected repository, so the same server
code serves the in-memory demo store and a real backing store unchanged.
"""

from mcp.server.fastmcp import FastMCP

from arp.mcp import tools
from arp.mcp.repository import Repository
from arp.tools import GET_PRODUCT, LOOKUP_ORDER, SEARCH_CATALOG, WRITE_ENRICHMENT


def build_server(repo: Repository, name: str = "arp-tools") -> FastMCP:
    server = FastMCP(name)

    def get_product(product_id: str) -> dict:
        """Fetch a single catalogue item by its identifier."""
        return tools.get_product(repo, product_id).model_dump()

    def search_catalog(query: str, k: int = 5) -> dict:
        """Keyword-search the catalogue and return at most k matching items."""
        return {"items": [item.model_dump() for item in tools.search_catalog(repo, query, k)]}

    def lookup_order(order_id: str) -> dict:
        """Fetch an order and its status by identifier."""
        return tools.lookup_order(repo, order_id).model_dump()

    def write_enrichment(product_id: str, attributes: dict) -> dict:
        """Persist enriched attributes for a product. Mutating: policy-gated."""
        tools.write_enrichment(repo, product_id, attributes)
        return {"product_id": product_id, "written": True}

    server.add_tool(get_product, name=GET_PRODUCT)
    server.add_tool(search_catalog, name=SEARCH_CATALOG)
    server.add_tool(lookup_order, name=LOOKUP_ORDER)
    server.add_tool(write_enrichment, name=WRITE_ENRICHMENT)
    return server
