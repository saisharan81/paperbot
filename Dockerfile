FROM python:3.11-slim

# Container image for running paperbot with Poetry-managed dependencies.

WORKDIR /app

ENV POETRY_VERSION=1.7.1

# Install build tools (for wheels) and Poetry, then clean up apt caches.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && pip install "poetry==$POETRY_VERSION" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-install dependencies (no local package) to leverage build cache.
COPY pyproject.toml .
RUN poetry install --no-root --only main

# Add application source and config.
COPY src/ ./src/
COPY config/ ./config/

ENV PYTHONPATH=/app/src

# Entrypoint runs the demo main module.
CMD ["poetry", "run", "python", "-m", "paperbot.main"]
