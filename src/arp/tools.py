"""The tool vocabulary shared by the registry, the policy layer and the MCP server.

Single source of truth: a name absent from here cannot be granted to an agent
(FR-002) and is not exposed over MCP (FR-003).
"""

SEARCH_CATALOG = "search_catalog"
GET_PRODUCT = "get_product"
WRITE_ENRICHMENT = "write_enrichment"
LOOKUP_ORDER = "lookup_order"

TOOL_CATALOG = frozenset({SEARCH_CATALOG, GET_PRODUCT, WRITE_ENRICHMENT, LOOKUP_ORDER})
