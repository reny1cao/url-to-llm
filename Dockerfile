# Root Dockerfile for Cloud Run automatic builds
# This builds the backend by default

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Cloud SQL Proxy dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional Cloud Run dependencies
RUN pip install --no-cache-dir \
    google-cloud-storage \
    google-cloud-secret-manager \
    psycopg2-binary \
    gunicorn

# Copy backend application code
COPY backend/ ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Port for Cloud Run (must be 8080 for automatic builds)
ENV PORT 8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Use gunicorn for production with uvicorn workers
CMD exec gunicorn app.main:app \
    --bind :$PORT \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 0 \
    --access-logfile - \
    --error-logfile -