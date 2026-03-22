# Minimal base image
FROM python:3.11-slim

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create a non-root user
RUN useradd -m -U -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Ensure data directory exists with subdirectories so bind mounts don't create them as root
RUN mkdir -p data/raw data/processed data/analytics data/state data/ai data/config/layouts && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Copy dependency files
COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./

# Install dependencies (frozen to lockfile, no dev dependencies)
RUN uv sync --frozen --no-dev

# Copy application source code
COPY --chown=appuser:appuser . .

# Expose Streamlit default port
EXPOSE 8501

# Start the application via entrypoint
ENTRYPOINT ["scripts/docker-entrypoint.sh"]
