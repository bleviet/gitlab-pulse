# Stage 1: Build the React/TypeScript frontend
FROM node:22-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: FastAPI runtime with uv
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd -m -U -s /bin/bash appuser

WORKDIR /app

RUN mkdir -p data/raw data/processed data/analytics data/state && \
    chown -R appuser:appuser /app

USER appuser

COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY --chown=appuser:appuser . .
COPY --chown=appuser:appuser --from=frontend-builder /frontend/dist ./frontend/dist

EXPOSE 8501

ENTRYPOINT ["scripts/docker-entrypoint.sh"]
