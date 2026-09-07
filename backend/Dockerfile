# ==============================================================================
# Plug-N-Play AI — Production Dockerfile
# Optimized multi-stage build with ONNX Runtime & non-root security
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools for native extensions (asyncpg, bcrypt, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Pre-download the FastEmbed ONNX model so cold-start queries resolve instantly
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# ==============================================================================
# Final Runtime Container
# ==============================================================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime dependencies (libpq for postgres client, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /root/.cache /root/.cache

# Copy application source code
COPY . /app

# Create non-root user for enterprise container security
RUN useradd -u 10001 -m -s /bin/sh appuser && \
    chown -R appuser:appuser /app /root/.cache 2>/dev/null || true

USER appuser

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
