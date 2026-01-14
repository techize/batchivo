# Multi-stage Dockerfile for FastAPI backend with Poetry
# Using Alpine for smaller image size and faster security updates

# Stage 1: Builder
FROM python:3.14-alpine as builder

WORKDIR /app

# Install build dependencies for Python packages that need compilation
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies to a virtual environment
RUN poetry config virtualenvs.in-project true && \
    poetry install --only main --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.14-alpine

WORKDIR /app

# Update packages, install runtime dependencies, and upgrade pip
RUN apk upgrade --no-cache && \
    apk add --no-cache libpq && \
    pip install --no-cache-dir --upgrade pip

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check using stdlib (no external dependencies)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
