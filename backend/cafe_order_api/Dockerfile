FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy package files
COPY backend/shared ./backend/shared
COPY backend/cafe_order_api ./backend/cafe_order_api

# Install dependencies from package directory
WORKDIR /app/backend/cafe_order_api
RUN uv sync --no-dev

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8005

# Run with multiple workers (default 4, override with WORKERS env var)
# Using uvicorn directly instead of python -m to support --workers flag
CMD ["uv", "run", "uvicorn", "cafe_order_api.app:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "4"]
