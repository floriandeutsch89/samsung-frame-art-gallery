# Stage 1: Build Vue frontend
FROM node:22-alpine AS frontend
WORKDIR /app
COPY src/frontend/package*.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

# Stage 2: Install Python dependencies (git needed for samsung-tv-ws-api)
FROM python:3.13-slim AS python-deps
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv --no-cache-dir --requirement requirements.txt

# Stage 3: Runtime — no build tools, no git
FROM python:3.13-slim
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=python-deps /opt/venv /opt/venv

RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /images && \
    chown -R appuser:appuser /app /app/data /images

COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser --from=frontend /app/dist ./static/
COPY --chown=appuser:appuser docker/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
