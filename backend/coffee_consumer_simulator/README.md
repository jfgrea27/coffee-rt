# Coffee Consumer Simulator

A Locust-based load testing tool that simulates customers ordering coffee drinks at various store locations.

## Installation

```bash
cd backend/coffee_consumer_simulator
uv sync
```

## Usage

### Web UI Mode

Start Locust with the web interface:

```bash
uv run locust -f src/coffee_consumer_simulator/locustfile.py --host http://localhost:8005
```

Then open http://localhost:8089 to configure and start the test.

### Headless Mode

Run without the web UI:

```bash
# 10 users, spawn rate of 2 users/second, run for 60 seconds
uv run locust -f src/coffee_consumer_simulator/locustfile.py \
    --host http://localhost:8005 \
    --headless \
    --users 10 \
    --spawn-rate 2 \
    --run-time 60s
```

### Run Specific User Classes

Run only certain user types:

```bash
# Only rush hour customers
uv run locust -f src/coffee_consumer_simulator/locustfile.py \
    --host http://localhost:8005 \
    RushHourCustomer

# Multiple specific types
uv run locust -f src/coffee_consumer_simulator/locustfile.py \
    --host http://localhost:8005 \
    CoffeeConsumer CappuccinoLover
```

## User Types

| User Class         | Description                                                  | Wait Time |
| ------------------ | ------------------------------------------------------------ | --------- |
| `CoffeeConsumer`   | General customer ordering various drinks at random locations | 1-5s      |
| `DowntownRegular`  | Customer who always orders at the downtown location          | 2-8s      |
| `CappuccinoLover`  | Customer who only orders cappuccinos                         | 3-10s     |
| `RushHourCustomer` | Fast-ordering customer simulating rush hour traffic          | 0.5-2s    |

## Drinks and Prices

| Drink      | Price Range   |
| ---------- | ------------- |
| Cappuccino | $4.50 - $6.50 |
| Americano  | $3.00 - $4.50 |
| Latte      | $4.00 - $6.00 |

## Store Locations

- uptown
- downtown
- central
- southend

## API Endpoints Tested

- `POST /api/order` - Create coffee orders
- `GET /api/dashboard` - Fetch dashboard metrics
- `GET /health` - Health check
