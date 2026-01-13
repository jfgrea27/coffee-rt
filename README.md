# Coffee-RT: Real-Time Order Analytics

A minimal, monolithic solution for real-time computation without stream frameworks.

[Architecture](#architecture) | [Quick Start](#quick-start) | [Scale Experiments](SCALE.md) | [Blog Post](BLOG.md)

---

## Why This Project?

This project explores **how far you can scale a simple architecture** before needing heavy frameworks like Kafka, Flink, or Spark Streaming.

The goal is not to build a production-ready system with authentication, rate limiting, or enterprise features. Instead, it's a controlled environment to:

- Measure throughput and latency limits of a basic stack
- Understand where bottlenecks emerge under load
- Establish baseline metrics for comparison with stream-processing solutions

Scale experiments and results are documented in [SCALE.md](SCALE.md).

---

## Key Features

- **Async FastAPI** with WebSocket streaming for real-time dashboard updates
- **Redis-cached metrics** computed by a scheduled aggregator (no real-time stream processing)
- **Prometheus + Grafana** observability stack
- **Kubernetes-ready** with Helm charts
- **70%+ test coverage** with CI enforcement
- **Locust load testing** with multiple customer behavior profiles

---

## Architecture

This project implements three different architectures for comparison:

### v1: Direct Database + Cron Aggregation

```
POST /api/v1/order → PostgreSQL → Aggregator (cron) → Redis → Dashboard
```

Simple and reliable. Orders write directly to PostgreSQL, a cron job computes metrics periodically.

### v2: Redis Streams + Stream Worker

```
POST /api/v2/order → Redis Stream → Stream Worker → PostgreSQL + Redis → Dashboard
```

Near real-time with batched writes. Orders go to Redis Streams, a Python worker batches inserts to PostgreSQL and updates metrics in Redis.

### v3: Kafka + Apache Flink

```
POST /api/v3/order → Kafka → Flink → PostgreSQL + Redis → Dashboard
```

Full stream processing. Orders published to Kafka, Flink handles windowed aggregations and database writes.

### Data Flow (all versions)

1. **Orders come in** via `POST /api/v{1,2,3}/order`
2. **Processing varies** by version (direct write, stream worker, or Flink)
3. **Dashboard reads from Redis** for fast cached metrics
4. **WebSocket pushes updates** to connected clients
5. **Prometheus scrapes** `/metrics` for operational observability

### Design Decisions

For a deeper dive into why these architectures were chosen, see [BLOG.md](BLOG.md).

---

## Tech Stack

| Component       | Technology                   |
| --------------- | ---------------------------- |
| API             | FastAPI (Python 3.13, async) |
| Database        | PostgreSQL 16                |
| Cache           | Redis 7                      |
| Stream (v2)     | Redis Streams + Python       |
| Stream (v3)     | Apache Kafka + Flink         |
| Metrics         | Prometheus + Grafana         |
| Logs            | Loki + Promtail              |
| Load Testing    | Locust                       |
| Orchestration   | Kubernetes + Helm            |
| CI/CD           | GitHub Actions               |
| Package Manager | uv                           |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose (or Colima with nerdctl)
- Python 3.13+ (or use the Nix flake)
- Node.js 18+ (for frontend)
- [just](https://github.com/casey/just) task runner (optional)

### Run Locally

The project supports three architecture versions that can be run independently:

```bash
# Clone and enter directory
git clone https://github.com/your-username/coffee-rt.git
cd coffee-rt

# Option 1: Run all versions (original behavior)
docker compose up -d
# Or with just: just nerdctl-up

# Option 2: Run specific version
# v1: Direct DB writes + cron aggregation
docker compose -f docker-compose.base.yaml -f docker-compose.v1.yaml up -d
# Or: just nerdctl-up-v1

# v2: Redis Streams + stream-worker
docker compose -f docker-compose.base.yaml -f docker-compose.v2.yaml up -d
# Or: just nerdctl-up-v2

# v3: Kafka + Flink stream processing
docker compose -f docker-compose.base.yaml -f docker-compose.v3.yaml up -d
# Or: just nerdctl-up-v3

# API available at http://localhost:8005
# Dashboard at http://localhost:3000
# Flink UI at http://localhost:8081 (v3 only)
```

### Run Tests

```bash
# All tests with coverage
just test-all

# Or manually
uv run pytest backend/cafe_order_api/tests -v --cov
```

### Run Load Tests

```bash
# Start Locust web UI
just load-test

# Or headless
locust -f backend/coffee_consumer_simulator/src/coffee_consumer_simulator/locustfile.py \
  --headless --users 100 --spawn-rate 10 --run-time 5m
```

---

## API Endpoints

| Endpoint         | Method | Description                    |
| ---------------- | ------ | ------------------------------ |
| `/api/v1/order`  | POST   | Create order (direct DB write) |
| `/api/v2/order`  | POST   | Create order (Redis Streams)   |
| `/api/v3/order`  | POST   | Create order (Kafka)           |
| `/api/dashboard` | GET    | Retrieve cached metrics        |
| `/ws/dashboard`  | WS     | Real-time dashboard updates    |
| `/metrics`       | GET    | Prometheus metrics             |
| `/livez`         | GET    | Liveness probe                 |
| `/readyz`        | GET    | Readiness probe                |

---

## Project Structure

```
coffee-rt/
├── backend/
│   ├── cafe_order_api/        # Main API service (all versions)
│   ├── cafe_order_aggregator/ # Cron-based metrics aggregator (v1)
│   ├── stream_worker/         # Redis Streams consumer (v2)
│   ├── coffee_consumer_simulator/ # Locust load tests
│   ├── db/                    # Alembic migrations
│   └── shared/                # Shared models and utilities
├── frontend/                  # React dashboard
├── flink/                     # Flink job for stream processing (v3)
├── helm/coffee-rt/            # Kubernetes Helm charts
├── docker-compose.yaml        # All versions combined
├── docker-compose.base.yaml   # Shared infrastructure (postgres, redis)
├── docker-compose.v1.yaml     # v1: Direct DB + cron aggregation
├── docker-compose.v2.yaml     # v2: Redis Streams + stream-worker
├── docker-compose.v3.yaml     # v3: Kafka + Flink
├── justfile                   # Task runner
└── SCALE.md                   # Scale experiment plans
```

---

## Scale Experiments

This project exists to answer: **How far can this simple architecture scale?**

Planned experiments include:

- Baseline throughput and latency measurements
- Spike testing and recovery behavior
- Database and Redis stress tests
- WebSocket connection limits
- Failure injection scenarios

See [SCALE.md](SCALE.md) for the full experiment plan and results.

---

## Roadmap

- [ ] Run and document scale experiments
- [ ] Deploy to cloud (AWS/GCP)
- [ ] Add Grafana dashboard exports
- [ ] Compare with Kafka-based solution

---

## License

MIT
