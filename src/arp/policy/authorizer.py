"""Tool authorization (FR-004).

The registry spec is the authority: a call outside `allowed_tools` is refused
here and never reaches the MCP server.
"""

from arp.registry import AgentSpec


class PolicyError(PermissionError):
    """Raised when an agent attempts a tool its spec does not grant.

    Carries the agent and tool as fields so the refusal can be traced verbatim
    rather than re-parsed from the message.
    """

    def __init__(self, agent_id: str, tool: str) -> None:
        self.agent_id = agent_id
        self.tool = tool
        super().__init__(f"agent '{agent_id}' is not allowed to call tool '{tool}'")


def is_allowed(spec: AgentSpec, tool: str) -> bool:
    return tool in spec.allowed_tools


def authorize(spec: AgentSpec, tool: str) -> None:
    if not is_allowed(spec, tool):
        raise PolicyError(spec.id, tool)
