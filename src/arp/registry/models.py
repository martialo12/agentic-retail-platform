"""What a registered agent *is* — the declarative contract behind FR-001."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from arp.tools import TOOL_CATALOG


class EscalationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_confidence: float = Field(ge=0.0, le=1.0)
    sensitive_intents: list[str] = Field(default_factory=list)


class AgentSpec(BaseModel):
    """Frozen on purpose: the spec is the authority on what an agent may do,
    so nothing downstream may widen its own permissions at runtime (FR-004)."""

    model_config = ConfigDict(frozen=True)

    id: str
    model: str
    allowed_tools: list[str]
    escalation: EscalationPolicy
    owner: str
    prompt_path: str

    @field_validator("allowed_tools")
    @classmethod
    def _tools_must_exist(cls, tools: list[str]) -> list[str]:
        unknown = sorted(set(tools) - TOOL_CATALOG)
        if unknown:
            known = ", ".join(sorted(TOOL_CATALOG))
            raise ValueError(f"unknown tool(s) {', '.join(unknown)}; known tools: {known}")
        return tools
