# Build the static bundle, then hand it to nginx. The bundle is the whole
# runtime — no Node, no source — so the shipped image is small and serves from
# an unprivileged nginx that already runs as a non-root user on 8080.
FROM node:22-bookworm-slim AS build

WORKDIR /app

# Lockfile-only install layer, cached across every source-only change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked at build time. The default suits the local compose demo (the API is
# reachable at localhost:8000, which its CORS allow-list already trusts); a real
# deploy overrides it with the API's own URL: --build-arg VITE_API_BASE=…
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build


FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="arp-console" \
      org.opencontainers.image.description="Web console for the agentic retail socle" \
      org.opencontainers.image.source="https://github.com/martialo12/agentic-retail-platform"

# Replace the image's default server with the SPA config (history fallback).
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
