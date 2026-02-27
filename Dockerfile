# Use a stable Python slim image
FROM python:3.11-slim

WORKDIR /app

# Ensure we don't write .pyc files or buffer output (better for logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    API_HOST=0.0.0.0 \
    API_PORT=8080

# Install dependencies directly (no compilation needed for core deps)
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    python-multipart>=0.0.6 \
    pydantic>=2.5.0 \
    pypdf>=6.5.0 \
    google-genai>=0.2.0 \
    python-dotenv>=1.0.0 \
    structlog>=23.2.0 \
    qdrant-client>=1.7.0 \
    requests>=2.31.0

# Copy application source
COPY src/ src/

# Create data directory for local persistence fallback
RUN mkdir -p data

EXPOSE 8080

# Health check (checks the /health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Start the server
CMD uvicorn src.app:app --host $API_HOST --port $PORT --log-level warning
