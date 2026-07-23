"""Domain entities shared across the socle (spec: Key Entities).

All instances are synthetic — no real customer data ever enters the system (FR-013).
"""

from pydantic import BaseModel, ConfigDict, Field


class CatalogueItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    specs: dict[str, str] = Field(default_factory=dict)
    category: str | None = None


class Order(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    status: str
    product_ids: list[str] = Field(default_factory=list)
    customer_ref: str | None = None
