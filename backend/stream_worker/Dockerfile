FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy package files
COPY backend/shared ./backend/shared
COPY backend/stream_worker ./backend/stream_worker

# Install dependencies from package directory
WORKDIR /app/backend/stream_worker
RUN uv sync --no-dev

# Run the worker (long-running process)
CMD ["uv", "run", "stream-worker"]
