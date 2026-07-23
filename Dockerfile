# Both stages share the same base image so the virtualenv built in `builder`
# keeps working when copied into `runtime` — its interpreter is an absolute path.
FROM python:3.11-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.3 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies resolve from the lockfile alone, so this layer is cached across
# every source-only change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra agents --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --extra agents --no-editable


FROM python:3.11-slim-bookworm AS runtime

# Synthetic corpus only — no real customer data is ever baked into the image.
LABEL org.opencontainers.image.title="agentic-retail-platform" \
      org.opencontainers.image.description="MCP tool server for the agentic retail socle" \
      org.opencontainers.image.source="https://github.com/martialo12/agentic-retail-platform"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080 \
    DATA_DIR=/app/data/synthetic

RUN useradd --create-home --uid 10001 arp

WORKDIR /app

COPY --from=builder --chown=arp:arp /app/.venv /app/.venv
COPY --chown=arp:arp data ./data

USER arp

EXPOSE 8080

CMD ["python", "-m", "arp.mcp"]
