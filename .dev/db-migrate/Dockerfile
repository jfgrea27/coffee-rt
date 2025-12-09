FROM python:3.13-alpine

WORKDIR /app/backend/db

# Install Alembic and dependencies
RUN pip install --no-cache-dir alembic sqlalchemy psycopg2-binary

# Copy alembic configuration and migrations
COPY backend/db/alembic.ini .
COPY backend/db/alembic ./alembic

# Set entrypoint to run migrations
ENTRYPOINT ["sh", "-c", "echo 'Running Alembic migrations...' && alembic upgrade head && echo 'Migrations completed successfully'"]
