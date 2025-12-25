# Colima profile (set via COLIMA_PROFILE env var)
colima_profile := env_var_or_default("COLIMA_PROFILE", "default")
colima := "colima --profile " + colima_profile

# Azure settings
azure_rg := "coffee-rt-dev-rg"
azure_bastion := "coffee-rt-dev-bastion"
azure_aks := "coffee-rt-dev-aks"

dev-setup:
    uv pip install -e ".[dev,lint,test]"
    # pre-commit
    pre-commit install

lint-check:
    ruff check .

lint-all: lint-check frontend-lint flink-lint

format:
    ruff format .
    ruff check . --fix

## Dev
# external services (for local dev with containerd)
nerdctl-external-services:
    {{colima}} nerdctl -- compose down -v
    {{colima}} nerdctl -- compose up --build postgres db-migrate redis redis-init

nerdctl-external-services-down:
    {{colima}} nerdctl -- compose down -v
connect_db:
    PGPASSWORD=coffee-rt_password psql -h localhost -p 5432 -U coffee-rt -d coffee-rt

## Backend
run project:
    (cd backend/{{project}} && uv run src/{{project}}/app.py)

## Frontend
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

## Flink
flink-lint:
    cd flink/coffee-rt-flink && mvn checkstyle:check -B

## Test
test project:
    cd backend/{{project}} && uv run pytest -v

test-all:
    cd backend/shared && uv run pytest -v
    cd backend/cafe_order_api && uv run pytest -v
    cd backend/cafe_order_aggregator && uv run pytest -v
    cd flink/coffee-rt-flink && mvn test -B
    cd frontend && npm test -- --run

# Flink tests
flink-test:
    cd flink/coffee-rt-flink && mvn test -B

flink-test-verbose:
    cd flink/coffee-rt-flink && mvn test

coverage project:
    cd backend/{{project}} && uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# Flink coverage
flink-coverage:
    cd flink/coffee-rt-flink && mvn clean verify -B
    @echo ""
    @echo "Coverage report: flink/coffee-rt-flink/target/site/jacoco/index.html"

# Flink coverage check (fails if below 60%)
flink-coverage-check:
    cd flink/coffee-rt-flink && mvn clean verify -B

coverage-all:
    rm -f .coverage
    cd backend/shared && uv run coverage run --source=src -m pytest
    cd backend/shared && uv run coverage report --show-missing
    cd backend/cafe_order_api && uv run coverage run --source=src -m pytest
    cd backend/cafe_order_api && uv run coverage report --show-missing
    cd backend/cafe_order_aggregator && uv run coverage run --source=src -m pytest
    cd backend/cafe_order_aggregator && uv run coverage report --show-missing
    cd frontend && npm test -- --coverage --run
    cd flink/coffee-rt-flink && mvn clean verify -B

## Docker

# v1: Direct DB writes + cron aggregation
nerdctl-up-v1:
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v1.yaml down -v
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v1.yaml up --build

# v2: Redis Streams + stream-worker
nerdctl-up-v2:
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v2.yaml down -v
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v2.yaml up --build

# v3: Kafka + Flink
nerdctl-up-v3:
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v3.yaml down -v
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v3.yaml up --build

nerdctl-down:
    {{colima}} nerdctl -- compose down -v
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v1.yaml down -v
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v2.yaml down -v
    {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.v3.yaml down -v


## Helm

helm-build-images:
    {{colima}} nerdctl -- build -t coffee-rt/cafe-order-api:latest -f backend/cafe_order_api/Dockerfile .
    {{colima}} nerdctl -- build -t coffee-rt/cafe-order-aggregator:latest -f backend/cafe_order_aggregator/Dockerfile.cron .
    {{colima}} nerdctl -- build -t coffee-rt/cafe-dashboard:latest -f frontend/Dockerfile frontend/
    {{colima}} nerdctl -- build -t coffee-rt/stream-worker:latest -f backend/stream_worker/Dockerfile .
    {{colima}} nerdctl -- build -t coffee-rt/flink-job:latest -f flink/coffee-rt-flink/Dockerfile flink/coffee-rt-flink/
    {{colima}} nerdctl -- build -t coffee-rt/db-migrate:latest -f backend/db/Dockerfile .

helm-import-images: helm-build-images
    {{colima}} nerdctl -- save coffee-rt/cafe-order-api:latest | {{colima}} nerdctl -- -n k8s.io load
    {{colima}} nerdctl -- save coffee-rt/cafe-order-aggregator:latest | {{colima}} nerdctl -- -n k8s.io load
    {{colima}} nerdctl -- save coffee-rt/cafe-dashboard:latest | {{colima}} nerdctl -- -n k8s.io load
    {{colima}} nerdctl -- save coffee-rt/stream-worker:latest | {{colima}} nerdctl -- -n k8s.io load
    {{colima}} nerdctl -- save coffee-rt/flink-job:latest | {{colima}} nerdctl -- -n k8s.io load
    {{colima}} nerdctl -- save coffee-rt/db-migrate:latest | {{colima}} nerdctl -- -n k8s.io load

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


helm-create-namespace:
    kubectl create namespace coffee-ns --dry-run=client -o yaml | kubectl apply -f -

# v1: Direct DB writes + cron aggregation (helm)
helm-deploy-v1: helm-import-images helm-pull-external-images helm-dep-update helm-create-namespace
    helm upgrade --install coffee-rt ./helm/coffee-rt -f ./helm/coffee-rt/values.deploy.v1.yaml -n coffee-ns

# v2: Redis Streams + stream-worker (helm)
helm-deploy-v2: helm-import-images helm-pull-external-images helm-dep-update helm-create-namespace
    helm upgrade --install coffee-rt ./helm/coffee-rt -f ./helm/coffee-rt/values.deploy.v2.yaml -n coffee-ns

# v3: Kafka + Flink (helm)
# helm-deploy-v3: helm-import-images helm-pull-external-images helm-dep-update helm-create-namespace
helm-deploy-v3:
    helm upgrade --install coffee-rt ./helm/coffee-rt -f ./helm/coffee-rt/values.deploy.v3.yaml -n coffee-ns

## Benchmarks

benchmark-ui:
    cd backend/coffee_consumer_simulator && uv run locust -f src/coffee_consumer_simulator/locustfile.py --host http://localhost:8005

# Headless benchmark for a single version
# Usage: just benchmark v1 5
benchmark version duration="5" users="100" rate="100" warmup="60":
    mkdir -p benchmark-results
    cd backend/coffee_consumer_simulator && uv run locust \
        -f src/coffee_consumer_simulator/benchmark.py \
        --host http://localhost:8005 \
        --api-version {{version}} \
        --headless \
        -u {{users}} \
        -r {{rate}} \
        -t {{duration}}s \
        --warmup-timeout {{warmup}} \
        --stop-timeout 5 \
        --csv ../../benchmark-results/{{version}} \
        --html ../../benchmark-results/{{version}}.html

# Spike test - sudden burst of traffic to test system resilience
# Usage: just benchmark-spike v1
benchmark-spike version users="500" duration="30" warmup="60":
    mkdir -p benchmark-results
    cd backend/coffee_consumer_simulator && uv run locust \
        -f src/coffee_consumer_simulator/benchmark.py \
        --host http://localhost:8005 \
        --api-version {{version}} \
        --headless \
        -u {{users}} \
        -r {{users}} \
        -t {{duration}}s \
        --warmup-timeout {{warmup}} \
        --stop-timeout 5 \
        --csv ../../benchmark-results/{{version}}_spike \
        --html ../../benchmark-results/{{version}}_spike.html

# E2E latency test - focuses on order-to-dashboard propagation time
# Usage: just benchmark-e2e v1
benchmark-e2e version users="50" duration="60" warmup="60":
    mkdir -p benchmark-results
    cd backend/coffee_consumer_simulator && uv run locust \
        -f src/coffee_consumer_simulator/benchmark.py \
        --host http://localhost:8005 \
        --api-version {{version}} \
        --headless \
        -u {{users}} \
        -r 10 \
        -t {{duration}}s \
        --warmup-timeout {{warmup}} \
        --stop-timeout 15 \
        --csv ../../benchmark-results/{{version}}_e2e \
        --html ../../benchmark-results/{{version}}_e2e.html
    @echo "Check E2E latency in the 'e2e_latency_{{version}}' row of the report"

# Breakpoint test - progressively increase load until failure threshold
# Usage: just benchmark-breakpoint v1
# For v3 (Kafka+Flink), use longer warmup: just benchmark-breakpoint v3 10 20 15 500 0.10 120
benchmark-breakpoint version start="10" step="20" interval="15" max="500" threshold="0.10" warmup="60":
    mkdir -p benchmark-results
    cd backend/coffee_consumer_simulator && uv run locust \
        -f src/coffee_consumer_simulator/benchmark.py \
        --host http://localhost:8005 \
        --api-version {{version}} \
        --headless \
        --breakpoint-mode \
        --breakpoint-start {{start}} \
        --breakpoint-step {{step}} \
        --breakpoint-interval {{interval}} \
        --breakpoint-max {{max}} \
        --breakpoint-threshold {{threshold}} \
        --warmup-timeout {{warmup}} \
        --stop-timeout 15 \
        --csv ../../benchmark-results/{{version}}_breakpoint \
        --html ../../benchmark-results/{{version}}_breakpoint.html

## Test Suites

# Wait for API health endpoint to be ready
[private]
wait-for-health version timeout="120":
    #!/usr/bin/env bash
    set -e
    echo "Waiting for API at http://localhost:8005/readyz..."
    for i in $(seq 1 {{timeout}}); do
        if curl -sf http://localhost:8005/readyz > /dev/null 2>&1; then
            echo "API is healthy after ${i}s"
            exit 0
        fi
        sleep 1
    done
    echo "Timeout waiting for API after {{timeout}}s"
    exit 1

# Internal: start cluster for a version
[private]
_cluster-up version build="true" replicas="1":
    #!/usr/bin/env bash
    if [[ "{{build}}" == "true" ]]; then
        {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.{{version}}.yaml up --build -d --scale cafe-order-api={{replicas}}
    else
        {{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.{{version}}.yaml up -d --scale cafe-order-api={{replicas}}
    fi

# Internal: stop cluster for a version (ignores errors if already down)
[private]
_cluster-down version:
    -{{colima}} nerdctl -- compose -f docker-compose.base.yaml -f docker-compose.{{version}}.yaml down -v

# Internal: run a single benchmark phase with fresh cluster
[private]
_run-benchmark-phase version phase benchmark_type users rate duration build="true" warmup="60":
    #!/usr/bin/env bash
    echo ""
    echo "=========================================="
    echo "Phase {{phase}}: {{benchmark_type}} benchmark for {{version}}"
    echo "=========================================="
    just _cluster-down {{version}} || true
    just _cluster-up {{version}} {{build}}
    just wait-for-health {{version}}
    mkdir -p benchmark-results
    # Run benchmark (allow failures - we still want results and clean shutdown)
    cd backend/coffee_consumer_simulator && uv run locust \
        -f src/coffee_consumer_simulator/benchmark.py \
        --host http://localhost:8005 \
        --api-version {{version}} \
        --workers 4 \
        --headless \
        -u {{users}} \
        -r {{rate}} \
        -t {{duration}}s \
        --warmup-timeout {{warmup}} \
        --stop-timeout 15 \
        --csv ../../benchmark-results/{{version}}_{{benchmark_type}} \
        --html ../../benchmark-results/{{version}}_{{benchmark_type}}.html \
        || echo "Benchmark completed with failures (exit code $?)"
    just _cluster-down {{version}} || true

# Internal: run breakpoint benchmark phase with fresh cluster
[private]
_run-breakpoint-phase version phase build="true" replicas="1" start="10" step="20" interval="15" max="500" threshold="0.10" warmup="60":
    #!/usr/bin/env bash
    echo ""
    echo "=========================================="
    echo "Phase {{phase}}: breakpoint benchmark for {{version}}"
    echo "=========================================="
    just _cluster-down {{version}} || true
    just _cluster-up {{version}} {{build}} {{replicas}}
    just wait-for-health {{version}}
    mkdir -p benchmark-results
    # Run breakpoint benchmark - stops automatically when failure rate threshold reached
    cd backend/coffee_consumer_simulator && uv run locust \
        -f src/coffee_consumer_simulator/benchmark.py \
        --host http://localhost:8005 \
        --workers 4 \
        --api-version {{version}} \
        --headless \
        --breakpoint-mode \
        --breakpoint-start {{start}} \
        --breakpoint-step {{step}} \
        --breakpoint-interval {{interval}} \
        --breakpoint-max {{max}} \
        --breakpoint-threshold {{threshold}} \
        --warmup-timeout {{warmup}} \
        --stop-timeout 15 \
        --csv ../../benchmark-results/{{version}}_breakpoint \
        --html ../../benchmark-results/{{version}}_breakpoint.html \
        || echo "Breakpoint test completed (exit code $?)"
    just _cluster-down {{version}} || true

# Full test suite for a version: standard, spike, e2e, and breakpoint benchmarks
# Usage: just test-suite v1
test-suite version build="true" replicas="1":
    @echo ""
    @echo "============================================================"
    @echo "Starting full test suite for {{version}}"
    @echo "============================================================"
    @echo ""
    # # Phase 1: Standard benchmark (500 users, gradual ramp)
    # just _run-benchmark-phase {{version}} 1 standard 500 50 120 {{build}}
    # # Phase 2: Spike benchmark (1000 users, instant ramp)
    # just _run-benchmark-phase {{version}} 2 spike 1000 1000 60 {{build}}
    # # Phase 3: E2E latency benchmark (100 users, moderate ramp)
    # just _run-benchmark-phase {{version}} 3 e2e 100 20 120 {{build}}
    # # Phase 4: Breakpoint benchmark (start=200, step=250, interval=10s, max=10000, threshold=50%, warmup=60s)
    just _run-breakpoint-phase {{version}} 4 {{build}} {{replicas}} 200 250 10 10000 0.25 60
    @echo ""
    @echo "============================================================"
    @echo "Test suite complete for {{version}}"
    @echo "Results saved to benchmark-results/"
    @echo "============================================================"
    @echo ""
    @echo "  Standard:   benchmark-results/{{version}}_standard.html"
    @echo "  Spike:      benchmark-results/{{version}}_spike.html"
    @echo "  E2E:        benchmark-results/{{version}}_e2e.html"
    @echo "  Breakpoint: benchmark-results/{{version}}_breakpoint.html"
    @echo ""
    -open benchmark-results/{{version}}_standard.html benchmark-results/{{version}}_spike.html benchmark-results/{{version}}_e2e.html benchmark-results/{{version}}_breakpoint.html

# Run full test suite for all versions (v1, v2, v3)
test-suite-all build="true" replicas="1":
    just test-suite v1 {{build}} {{replicas}}
    just test-suite v2 {{build}} {{replicas}}
    just test-suite v3 {{build}} {{replicas}}
    @echo ""
    @echo "============================================================"
    @echo "All test suites complete!"
    @echo "============================================================"
    @echo ""
    @echo "Opening all reports..."
    -open benchmark-results/v1_standard.html benchmark-results/v1_spike.html benchmark-results/v1_e2e.html benchmark-results/v1_breakpoint.html
    -open benchmark-results/v2_standard.html benchmark-results/v2_spike.html benchmark-results/v2_e2e.html benchmark-results/v2_breakpoint.html
    -open benchmark-results/v3_standard.html benchmark-results/v3_spike.html benchmark-results/v3_e2e.html benchmark-results/v3_breakpoint.html

## Azure Infrastructure

# Connect to bastion VM via SSH (optionally with port forwarding)
# Usage: just connect-bastion        # plain SSH
#        just connect-bastion 8080   # forward local:8080 -> bastion:8080
connect-bastion port="":
    #!/usr/bin/env bash
    BASTION_IP=$(az vm list-ip-addresses \
        --resource-group {{azure_rg}} \
        --name {{azure_bastion}} \
        --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
    if [ -n "{{port}}" ]; then
        echo "Connecting to bastion at $BASTION_IP with port forward localhost:{{port}} -> bastion:{{port}}..."
        ssh -L {{port}}:localhost:{{port}} -i ~/.ssh/id_rsa_azure azureuser@$BASTION_IP
    else
        echo "Connecting to bastion at $BASTION_IP..."
        ssh -i ~/.ssh/id_rsa_azure azureuser@$BASTION_IP
    fi
