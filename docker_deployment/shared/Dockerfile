# Multi-stage Docker build for kiro-project
FROM python:3.12-slim AS builder

# Install system dependencies needed for building (optimized for space)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to virtual environment
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.12-slim AS production

# Accept VERSION build argument
ARG VERSION
ENV APP_VERSION=${VERSION}

# Install runtime system dependencies (optimized for space)
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    libmagic1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* \
    && find /usr/share/doc -type f -delete \
    && find /usr/share/man -type f -delete

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser main.py ./
COPY --chown=appuser:appuser CLAUDE.md ./

# Create version file with build version info
RUN echo "${VERSION:-unknown}" > /app/VERSION \
    && chown appuser:appuser /app/VERSION

# Environment variables are configured by docker-compose.yml
# No .env files copied - all config via docker-compose environment section

# Create necessary directories with proper structure
RUN mkdir -p /app/data/source /app/data/saved /app/data/error /app/data/chroma_db /app/logs \
    && chown -R appuser:appuser /app/data /app/logs

# Create home directory for appuser and set proper permissions
RUN mkdir -p /home/appuser \
    && chown -R appuser:appuser /home/appuser \
    && chmod 755 /home/appuser

# Create temp directory for unstructured processing
RUN mkdir -p /tmp/unstructured \
    && chown -R appuser:appuser /tmp/unstructured \
    && chmod 755 /tmp/unstructured

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "main.py"]
