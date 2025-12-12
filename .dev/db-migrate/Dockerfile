FROM python:3.13-alpine

WORKDIR /app/backend/db

# Install Alembic and dependencies
RUN pip install --no-cache-dir alembic sqlalchemy psycopg2-binary

# Copy alembic configuration and migrations
COPY backend/db/alembic.ini .
COPY backend/db/alembic ./alembic

# Wait for postgres and run migrations
# nerdctl doesn't respect depends_on health checks, so we need to wait here
ENTRYPOINT ["sh", "-c", "\
    echo 'Waiting for PostgreSQL...' && \
    for i in 1 2 3 4 5 6 7 8 9 10; do \
        python -c \"import psycopg2; psycopg2.connect('$DATABASE_URL')\" 2>/dev/null && break; \
        echo \"Attempt $i: PostgreSQL not ready, waiting...\"; \
        sleep 2; \
    done && \
    echo 'Running Alembic migrations...' && \
    alembic upgrade head && \
    echo 'Migrations completed successfully'"]
