dev-setup:
    uv pip install -e ".[dev,lint,test]"
    # pre-commit
    pre-commit install

lint-check:
    ruff check .

format:
    ruff format .
    ruff check . --fix


# external services
docker-external-services:
    docker compose down -v
    docker compose up --build postgres db-migrate redis

docker-external-services-down:
    docker compose down -v

integration-test:
    .dev/integration_test/script.sh

connect_db:
    PGPASSWORD=coffee-rt_password psql -h localhost -p 5432 -U coffee-rt -d coffee-rt

run project:
    (cd backend/{{project}} && uv run src/{{project}}/app.py)

# Frontend commands
frontend-install:
    cd frontend && npm install

frontend-dev:
    cd frontend && npm run dev

frontend-build:
    cd frontend && npm run build

frontend-test:
    cd frontend && npm test -- --run

frontend-test-watch:
    cd frontend && npm test

frontend-lint:
    cd frontend && npx tsc --noEmit

test project:
    cd backend/{{project}} && uv run pytest -v

test-all:
    cd backend/shared && uv run pytest -v
    cd backend/cafe_order_api && uv run pytest -v
    cd backend/cafe_order_aggregator && uv run pytest -v
    cd frontend && npm test -- --run

coverage project:
    cd backend/{{project}} && uv run pytest --cov=src --cov-report=term-missing --cov-report=html

coverage-all:
    rm -f .coverage
    cd backend/shared && uv run coverage run --source=src -m pytest
    cd backend/shared && uv run coverage report --show-missing
    cd backend/cafe_order_api && uv run coverage run --source=src -m pytest
    cd backend/cafe_order_api && uv run coverage report --show-missing
    cd backend/cafe_order_aggregator && uv run coverage run --source=src -m pytest
    cd backend/cafe_order_aggregator && uv run coverage report --show-missing
    cd frontend && npm test -- --coverage
