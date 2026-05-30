# syntax=docker/dockerfile:1.7
#
# AtlasLens frontend — multi-stage build, served from Container Apps via nginx.
#
# Stage 1 builds the Vite bundle. Stage 2 ships nginx with our reverse-proxy
# config that forwards /api/* to the backend Container App. This lets the
# frontend and backend share an origin from the browser's point of view
# (no CORS, simpler cookies/JWT), while keeping the backend FQDN private to
# the Container Apps environment.

# ---------- builder ----------
FROM node:22-alpine AS builder

WORKDIR /build

ENV PNPM_HOME=/usr/local/pnpm \
    PATH=/usr/local/pnpm:$PATH \
    CI=true

RUN corepack enable && corepack prepare pnpm@11.1.1 --activate

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile=false

COPY frontend/ ./

# VITE_API_BASE is left empty so the browser hits the same origin (nginx
# forwards /api/* server-side).
ENV VITE_API_BASE=""

RUN pnpm build

# ---------- runtime ----------
FROM nginx:1.27-alpine AS runtime

COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=builder /build/dist /usr/share/nginx/html

ENV BACKEND_URL="" \
    PORT=8080

EXPOSE 8080

# nginx's official entrypoint substitutes env vars in /etc/nginx/templates/*.template
# and writes the result to /etc/nginx/conf.d/. We just need BACKEND_URL and PORT.
