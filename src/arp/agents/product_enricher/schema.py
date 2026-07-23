"""The contract the enricher's output must satisfy (FR-010).

Nothing leaves the agent without passing this schema — that is the whole point
of FR-008: a parse failure is a retry, then an escalation, never a silent emit.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnrichedProduct(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    materials: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    seo_description: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("category", "seo_description")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped
