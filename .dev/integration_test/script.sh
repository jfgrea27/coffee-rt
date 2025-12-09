#!/bin/bash
set -e

# Integration test script for coffee-rt
# This script:
# 1. Starts all services via docker compose
# 2. Waits for services to be healthy
# 3. Posts a coffee order via the API
# 4. Queries the database to verify the order was inserted
# 5. Cleans up

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    log_info "Cleaning up..."
    cd "$PROJECT_ROOT"
    docker compose down -v --remove-orphans 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting integration tests..."

# Clean up any existing containers
log_info "Cleaning up existing containers..."
docker compose down -v --remove-orphans 2>/dev/null || true

# Start all services
log_info "Starting docker compose services..."
docker compose up -d --build

# Wait for services to be ready
log_info "Waiting for services to be healthy..."

MAX_RETRIES=60
RETRY_COUNT=0

# Wait for cafe-order-api to be healthy
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8005/health > /dev/null 2>&1; then
        log_info "cafe-order-api is healthy"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "cafe-order-api failed to become healthy after $MAX_RETRIES attempts"
        docker compose logs cafe-order-api
        exit 1
    fi
    sleep 2
done

# Test 1: Health check
log_info "Test 1: Checking health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8005/health)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    log_info "Health check passed"
else
    log_error "Health check failed: $HEALTH_RESPONSE"
    exit 1
fi

# Test 2: Create a coffee order
log_info "Test 2: Creating a coffee order..."
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
ORDER_RESPONSE=$(curl -s -X POST http://localhost:8005/api/order \
    -H "Content-Type: application/json" \
    -d "{
        \"drink\": \"Latte\",
        \"store\": \"Downtown\",
        \"price\": 4.50,
        \"timestamp\": \"$TIMESTAMP\"
    }")

# Extract order ID from response
ORDER_ID=$(echo "$ORDER_RESPONSE" | grep -o '"id":[0-9]*' | grep -o '[0-9]*')

if [ -z "$ORDER_ID" ]; then
    log_error "Failed to create order. Response: $ORDER_RESPONSE"
    exit 1
fi

log_info "Order created with ID: $ORDER_ID"

# Test 3: Verify order in database
log_info "Test 3: Verifying order in database..."
DB_RESULT=$(docker compose exec -T postgres psql -U coffee-rt -d coffee-rt -t -c \
    "SELECT id, drink, store, price FROM coffee_rt.orders WHERE id = $ORDER_ID;")

if echo "$DB_RESULT" | grep -q "Latte"; then
    log_info "Order verified in database"
else
    log_error "Order not found in database. Query result: $DB_RESULT"
    exit 1
fi

# Verify all fields
if echo "$DB_RESULT" | grep -q "Downtown" && echo "$DB_RESULT" | grep -q "4.5"; then
    log_info "All order fields verified correctly"
else
    log_error "Order fields mismatch. Expected drink=Latte, store=Downtown, price=4.50"
    log_error "Got: $DB_RESULT"
    exit 1
fi

# Test 4: Create multiple orders and verify count
log_info "Test 4: Creating multiple orders..."
for i in {1..3}; do
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    curl -s -X POST http://localhost:8005/api/order \
        -H "Content-Type: application/json" \
        -d "{
            \"drink\": \"Espresso\",
            \"store\": \"Uptown\",
            \"price\": 3.00,
            \"timestamp\": \"$TIMESTAMP\"
        }" > /dev/null
done

ORDER_COUNT=$(docker compose exec -T postgres psql -U coffee-rt -d coffee-rt -t -c \
    "SELECT COUNT(*) FROM coffee_rt.orders;")
ORDER_COUNT=$(echo "$ORDER_COUNT" | tr -d ' ')

if [ "$ORDER_COUNT" -ge 4 ]; then
    log_info "Multiple orders created successfully. Total orders: $ORDER_COUNT"
else
    log_error "Expected at least 4 orders, got: $ORDER_COUNT"
    exit 1
fi

echo ""
log_info "=========================================="
log_info "All integration tests passed!"
log_info "=========================================="
