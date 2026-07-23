"""MCP layer. Note: `arp.mcp` shadows nothing — absolute imports inside this
package still resolve `mcp` to the third-party SDK."""

from arp.mcp.repository import InMemoryRepository, Repository
from arp.mcp.server import build_server

__all__ = ["InMemoryRepository", "Repository", "build_server"]
