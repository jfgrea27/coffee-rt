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

# Run the application
CMD ["uv", "run", "python", "-m", "cafe_order_api.app"]
