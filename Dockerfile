# Muninn MCP Memory Server
# Multi-stage build for minimal image size

FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Build wheel
RUN uv build --wheel

# --- Runtime stage ---
FROM python:3.13-slim

WORKDIR /app

# Install uv for pip install
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install the built wheel with HTTP extras
COPY --from=builder /app/dist/*.whl /tmp/
RUN uv pip install /tmp/*.whl uvicorn starlette --system && \
    rm -f /tmp/*.whl

# Create data directory for SQLite
RUN mkdir -p /data
ENV MUNINN_DB_PATH=/data/muninn.db

# Expose HTTP port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run HTTP transport by default
ENTRYPOINT ["muninn"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
