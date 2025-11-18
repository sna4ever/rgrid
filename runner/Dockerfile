FROM python:3.11-slim

# Install system dependencies (Docker CLI for executing jobs)
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
# Copy common library first (for better layer caching)
COPY common/ /app/common/

# Copy runner code
COPY runner/ /app/runner/

# Install Python dependencies
WORKDIR /app

# Install common library (contains shared models and utilities)
RUN pip install --no-cache-dir -e /app/common

# Install runner dependencies
RUN pip install --no-cache-dir \
    sqlalchemy \
    asyncpg \
    psycopg2-binary \
    docker \
    boto3 \
    minio \
    httpx

# Set working directory to runner
WORKDIR /app/runner

# Environment variables (will be overridden by cloud-init)
ENV DATABASE_URL=""
ENV WORKER_ID=""
ENV PYTHONPATH=/app

# Health check (optional - checks if worker process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD ps aux | grep -q '[p]ython -m runner.worker' || exit 1

# Run the worker daemon
CMD ["python", "-m", "runner.worker"]
