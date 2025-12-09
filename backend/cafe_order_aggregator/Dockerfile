FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy package files
COPY backend/shared ./backend/shared
COPY backend/cafe_order_aggregator ./backend/cafe_order_aggregator

# Install dependencies from package directory
WORKDIR /app/backend/cafe_order_aggregator
RUN uv sync --no-dev

# Run the aggregator
CMD ["uv", "run", "cafe-aggregator"]
