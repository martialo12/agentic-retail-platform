"""The contract the assistant's replies must satisfy (FR-011)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssistantReply(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    tool_calls_used: list[str] = Field(default_factory=list)
    escalate: bool = False

    @field_validator("answer")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped
