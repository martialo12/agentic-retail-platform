# Build the static bundle, then hand it to nginx. The bundle is the whole
# runtime — no Node, no source — so the shipped image is small and serves from
# an unprivileged nginx that already runs as a non-root user on 8080.
FROM node:22-bookworm-slim AS build

WORKDIR /app

# Lockfile-only install layer, cached across every source-only change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build-time fallback only. The deployed console resolves its API at start-up
# from the API_BASE environment variable (see docker-entrypoint.d), because the
# API's URL does not exist until the platform is applied. This default suits the
# local compose demo, whose CORS allow-list already trusts localhost:8000.
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build


FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="arp-console" \
      org.opencontainers.image.description="Web console for the agentic retail socle" \
      org.opencontainers.image.source="https://github.com/martialo12/agentic-retail-platform"

# Replace the image's default server with the SPA config (history fallback).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Owned by the runtime user: the entrypoint rewrites config.js in place, and
# nginx-unprivileged runs as uid 101, not root.
COPY --from=build --chown=101:101 /app/dist /usr/share/nginx/html
COPY --chmod=755 docker-entrypoint.d/40-arp-api-base.sh /docker-entrypoint.d/

EXPOSE 8080
