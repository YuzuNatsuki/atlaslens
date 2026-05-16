# syntax=docker/dockerfile:1.7
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OS-level deps for crypto wheels etc.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better caching)
COPY backend/pyproject.toml backend/README.md /app/
RUN pip install --upgrade pip \
    && pip install .

# Copy backend source, seed data, and Prompt Flow DAG
COPY backend/app /app/app
COPY data /app/data
COPY infra/prompt_flow /app/prompt_flow

ENV DATA_DIR=/app/data/atlascorp \
    APP_ENV=container \
    PROMPT_FLOW_DIR=/app/prompt_flow/org_impact \
    PROMPT_FLOW_CONNECTION_STORE=/tmp/pf-connections \
    PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring \
    PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
