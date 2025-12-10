# Colima profile (set via COLIMA_PROFILE env var)
colima_profile := env_var_or_default("COLIMA_PROFILE", "default")
colima := "colima --profile " + colima_profile

dev-setup:
    uv pip install -e ".[dev,lint,test]"
    # pre-commit
    pre-commit install

lint-check:
    ruff check .

format:
    ruff format .
    ruff check . --fix


# external services (for local dev with containerd)
nerdctl-external-services:
    {{colima}} nerdctl -- compose down -v
    {{colima}} nerdctl -- compose up --build postgres db-migrate redis redis-init

nerdctl-external-services-down:
    {{colima}} nerdctl -- compose down -v
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


nerdctl-up:
    {{colima}} nerdctl -- compose up --build

nerdctl-down:
    {{colima}} nerdctl -- compose down -v

helm-build-images:
    {{colima}} nerdctl -- build -t coffee-rt/cafe-order-api:latest -f backend/cafe_order_api/Dockerfile .
    {{colima}} nerdctl -- build -t coffee-rt/cafe-order-aggregator:latest -f backend/cafe_order_aggregator/Dockerfile.cron .
    {{colima}} nerdctl -- build -t coffee-rt/cafe-dashboard:latest -f frontend/Dockerfile frontend/

helm-import-images: helm-build-images
    {{colima}} nerdctl -- save coffee-rt/cafe-order-api:latest | {{colima}} nerdctl -- -n k8s.io load
    {{colima}} nerdctl -- save coffee-rt/cafe-order-aggregator:latest | {{colima}} nerdctl -- -n k8s.io load
    {{colima}} nerdctl -- save coffee-rt/cafe-dashboard:latest | {{colima}} nerdctl -- -n k8s.io load

helm-list-images:
    {{colima}} nerdctl -- -n k8s.io images | grep -E "coffee-rt|redis|postgresql"

helm-pull-external-images:
    {{colima}} nerdctl -- -n k8s.io pull bitnami/redis:latest
    {{colima}} nerdctl -- -n k8s.io pull bitnami/postgresql:latest

helm-dep-update:
    cd helm/coffee-rt && helm dependency update

helm-lint:
    cd helm/coffee-rt && helm lint . -f values.dev.yaml

helm-template:
    cd helm/coffee-rt && helm template coffee-rt . -f values.dev.yaml

helm-install: helm-dep-update
    helm install coffee-rt ./helm/coffee-rt -f ./helm/coffee-rt/values.dev.yaml

helm-upgrade:
    helm upgrade coffee-rt ./helm/coffee-rt -f ./helm/coffee-rt/values.dev.yaml

helm-uninstall:
    helm uninstall coffee-rt

helm-deploy: helm-import-images helm-pull-external-images helm-dep-update
    kubectl create namespace coffee-ns --dry-run=client -o yaml | kubectl apply -f -
    helm upgrade --install coffee-rt ./helm/coffee-rt -f ./helm/coffee-rt/values.dev.yaml -n coffee-ns


load-test:
    cd backend/coffee_consumer_simulator && uv run locust -f src/coffee_consumer_simulator/locustfile.py --host http://localhost:8005
