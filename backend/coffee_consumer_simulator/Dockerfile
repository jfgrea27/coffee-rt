FROM python:3.12-slim

WORKDIR /app

# Install uv and azure cli
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy package files
COPY backend/coffee_consumer_simulator ./backend/coffee_consumer_simulator

# Install dependencies from package directory
WORKDIR /app/backend/coffee_consumer_simulator
RUN uv sync --no-dev

# Create results directory
RUN mkdir -p /results

# Default environment variables
ENV API_VERSION="v2"
ENV TARGET_HOST="http://coffee-rt-api:8005"
ENV BREAKPOINT_START="10"
ENV BREAKPOINT_STEP="10"
ENV BREAKPOINT_INTERVAL="15"
ENV BREAKPOINT_MAX="500"
ENV BREAKPOINT_THRESHOLD="0.10"

# Run the load test wrapper script
CMD ["uv", "run", "python", "-m", "coffee_consumer_simulator.run_load_test"]
