"""HTTP surface for the console.

Deliberately unauthenticated (FR-018). The IaC is what keeps this non-public —
internal ingress and an empty invoker set — rather than a warning in a README.
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from arp.api.streaming import stream_run
from arp.api.wiring import Deps, build_assistant_graph, build_deps, build_enricher_graph

# Proxies buffer by default, which would defeat the whole point of streaming.
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class AskRequest(BaseModel):
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class EnrichRequest(BaseModel):
    product_id: str = Field(min_length=1)


def create_app(deps: Deps | None = None) -> FastAPI:
    app = FastAPI(title="Agentic Retail Platform", version="0.1.0")

    # The front runs on Vite's port in development, so it is a different origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:4173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_deps() -> Deps:
        return deps if deps is not None else build_deps()

    D = Annotated[Deps, Depends(get_deps)]

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/catalogue")
    def catalogue(d: D) -> dict:
        return {"items": [item.model_dump() for item in d.repo.list_products()]}

    @app.post("/api/assistant/ask")
    def ask(request: AskRequest, d: D) -> StreamingResponse:
        return StreamingResponse(
            stream_run(
                d,
                "customer-assistant",
                build_assistant_graph,
                {"question": request.question},
            ),
            media_type="text/event-stream",
            headers=STREAM_HEADERS,
        )

    @app.post("/api/enricher/enrich")
    def enrich(request: EnrichRequest, d: D) -> StreamingResponse:
        sheet = d.repo.get_product(request.product_id)
        if sheet is None:
            raise HTTPException(status_code=404, detail=f"unknown product {request.product_id}")
        return StreamingResponse(
            stream_run(d, "product-enricher", build_enricher_graph, {"sheet": sheet.model_dump()}),
            media_type="text/event-stream",
            headers=STREAM_HEADERS,
        )

    @app.get("/api/runs")
    def runs(
        d: D,
        agent: str | None = None,
        outcome: str | None = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict:
        items = d.run_store.list(agent=agent, outcome=outcome, limit=limit, offset=offset)
        return {"items": [item.model_dump(mode="json") for item in items], "total": len(items)}

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str, d: D) -> dict:
        record = d.run_store.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"unknown run {run_id}")
        return record

    return app
