# Stage 1: Build Vue frontend
FROM node:22-alpine AS frontend
WORKDIR /app
COPY src/frontend/package*.json ./
RUN npm install
COPY src/frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.13-slim

WORKDIR /app

# Install git and uv
RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /thumbnails /app/data && \
    chown -R appuser:appuser /app /thumbnails /app/data

COPY pyproject.toml requirements.txt ./
RUN /root/.local/bin/uv pip install --system --no-cache-dir --requirement requirements.txt

COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser --from=frontend /app/dist ./static/
COPY --chown=appuser:appuser docker/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
