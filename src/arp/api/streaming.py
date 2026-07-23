"""Turn a run into a Server-Sent Events stream.

The tracer's sink pushes events into a queue while the graph runs as a task, and
we drain that queue into frames. That is what makes the console *show* the socle
working rather than report on it afterwards (SC-008).
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from arp.api.wiring import Deps
from arp.llmops.tracing import trace_run

DONE = "[DONE]"


def sse(payload: dict[str, Any] | str) -> str:
    body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return f"data: {body}\n\n"


async def stream_run(
    deps: Deps,
    agent_id: str,
    build_graph: Callable[[Deps, Any], Any],
    initial_state: dict[str, Any],
) -> AsyncIterator[str]:
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def sink(event: dict[str, Any]) -> None:
        # The tracer is synchronous and the graph may call it from a worker
        # thread, so hop back onto the loop rather than assuming we are on it.
        loop.call_soon_threadsafe(queue.put_nowait, event)

    async def run() -> None:
        try:
            with trace_run(
                agent_id,
                provider=deps.settings.llm_provider,
                sink=sink,
                store=deps.run_store,
            ) as tracer:
                await build_graph(deps, tracer).ainvoke(initial_state)
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as a frame
            await queue.put({"kind": "error", "message": f"{type(exc).__name__}: {exc}"})
        finally:
            await queue.put(None)

    task = asyncio.create_task(run())
    try:
        while (event := await queue.get()) is not None:
            yield sse(event)
        yield sse(DONE)
    finally:
        # A closed browser tab must not leave a run burning tokens.
        if not task.done():
            task.cancel()
