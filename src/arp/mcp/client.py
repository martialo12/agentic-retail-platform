"""The agent's only way to reach a tool (FR-003 + FR-004).

Every call is authorized against the calling agent's spec *before* it reaches the
server, and traced either way. A refusal is recorded and raised — never executed,
never silently dropped.
"""

import json
from typing import Any

from arp.llmops.tracing import EventKind, RunTracer
from arp.policy import PolicyError, authorize
from arp.registry import AgentSpec


class ToolClient:
    def __init__(self, server: Any, spec: AgentSpec, tracer: RunTracer | None = None) -> None:
        self._server = server
        self._spec = spec
        self._tracer = tracer

    async def call(self, tool: str, **arguments: Any) -> dict:
        try:
            authorize(self._spec, tool)
        except PolicyError:
            self._trace(tool, refused=True)
            raise

        result = await self._server.call_tool(tool, arguments)
        self._trace(tool, refused=False)
        return _payload(result)

    def _trace(self, tool: str, refused: bool) -> None:
        if self._tracer is not None:
            self._tracer.event(
                EventKind.TOOL_CALL, tool=tool, agent_id=self._spec.id, refused=refused
            )


def _payload(result: Any) -> dict:
    """FastMCP returns content blocks; tool results travel as JSON text."""
    if isinstance(result, list) and result:
        return json.loads(result[0].text)
    return result if isinstance(result, dict) else {}
