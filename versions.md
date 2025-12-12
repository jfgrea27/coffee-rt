# API Versioning Implementation

## Overview

Three API versions to compare different order ingestion patterns:

```
POST /api/v1/order  → Direct PostgreSQL (sync, batch aggregation)
POST /api/v2/order  → Redis Streams → worker → PostgreSQL + Redis (durable async, REAL-TIME)
POST /api/v3/order  → Kafka → Apache Flink → PostgreSQL + Redis (REAL-TIME)
```

---

## Data Flow Diagrams

### v1: Direct PostgreSQL (Batch)

```
┌──────────┐     ┌────────────┐     ┌───────────────────┐     ┌───────┐
│   API    │────▶│ PostgreSQL │◀────│ aggregator (cron) │────▶│ Redis │
│ /api/v1  │     │  (orders)  │     │   every 10-60s    │     │ cache │
└──────────┘     └────────────┘     └───────────────────┘     └───────┘
                                                                   │
                                                              ┌────▼────┐
                                                              │Dashboard│
                                                              └─────────┘
```

**Latency to dashboard:** 10-60 seconds (batch interval)

---

### v2: Redis Streams (Durable Async + Real-Time Metrics)

```
┌──────────┐     ┌───────────────┐     ┌───────────────┐     ┌────────────┐
│   API    │────▶│  Redis XADD   │────▶│ stream-worker │────▶│ PostgreSQL │
│ /api/v2  │     │ orders:stream │     │ (XREADGROUP)  │     │  (orders)  │
└──────────┘     └───────────────┘     └───────┬───────┘     └────────────┘
                                               │
                                               │ (real-time)
                                               ▼
                                         ┌───────────┐
                                         │   Redis   │◀── REAL-TIME!
                                         │  metrics  │
                                         └─────┬─────┘
                                               │
                                          ┌────▼────┐
                                          │Dashboard│
                                          └─────────┘
```

**Latency to dashboard:** ~50-100ms (real-time stream processing)
**Delivery guarantee:** At-least-once (messages persist in stream until ACKed)
**Replay capability:** Yes - can re-read unacknowledged messages on worker restart
**Processing:** stream-worker handles both PostgreSQL writes and Redis metric updates

---

### v3: Kafka with Apache Flink (REAL-TIME)

```
┌──────────┐     ┌─────────────────────────────────────────────────────┐
│   API    │────▶│                  Kafka (orders topic)               │
│ /api/v3  │     └─────────────────────────────────────────────────────┘
└──────────┘                    │                    │
                                │                    │
                    ┌───────────▼───────────┐  ┌─────▼─────────────────┐
                    │     kafka-worker      │  │   kafka-aggregator    │
                    │ (group: order-workers)│  │(group: order-aggregators)
                    └───────────┬───────────┘  └─────┬─────────────────┘
                                │                    │
                                ▼                    ▼
                        ┌────────────┐         ┌───────┐
                        │ PostgreSQL │         │ Redis │ ◀── REAL-TIME!
                        │  (orders)  │         │ cache │
                        └────────────┘         └───────┘
                                                    │
                                               ┌────▼────┐
                                               │Dashboard│
                                               └─────────┘
```

**Latency to dashboard:** ~100ms (real-time stream processing)
**Delivery guarantee:** Exactly-once (via message_id deduplication + Flink checkpointing)
**Durability:** Messages persist in Kafka, replayed on failure
**Processing:** Single Flink job handles both PostgreSQL writes and Redis aggregation

---

## Comparison Table

| Aspect                  | v1 (Direct)  | v2 (Streams)      | v3 (Kafka + Flink) |
| ----------------------- | ------------ | ----------------- | ------------------ |
| **API Response Time**   | ~10-20ms     | ~2-5ms            | ~5-10ms            |
| **Dashboard Latency**   | 10-60s       | ~50-100ms         | ~100ms             |
| **Delivery Guarantee**  | Exactly-once | At-least-once     | Exactly-once       |
| **Message Persistence** | N/A          | Durable (Redis)   | Durable (Kafka)    |
| **Replay Capability**   | N/A          | Yes (pending)     | Yes (full history) |
| **Worker Downtime**     | N/A          | Messages queued   | Messages queued    |
| **Aggregation**         | Batch (cron) | Real-time (worker)| Real-time (Flink)  |
| **Scalability**         | Single node  | Consumer groups   | Horizontally scalable |

---

## Services by Version

### v1 Services

- `cafe-order-api` - Direct PostgreSQL writes
- `cafe-order-aggregator` - Batch aggregation (cron)

### v2 Services

- `cafe-order-api` - Adds orders to Redis Stream (XADD)
- `stream-worker` - Consumes from stream (XREADGROUP), writes to PostgreSQL, and updates Redis metrics
- `cafe-order-aggregator` - Optional reconciliation (can be disabled for v2)

### v3 Services

- `cafe-order-api` - Produces to Kafka topic
- `flink-jobmanager` - Apache Flink cluster manager
- `flink-taskmanager` - Apache Flink task executor
- `flink-job` - Coffee order stream processing job (writes to PostgreSQL + Redis)
- `cafe-order-aggregator` - Optional reconciliation (can be disabled for v3)

---

## Kafka Consumer Groups

v3 uses a single Flink consumer group:

```
Kafka Topic: orders
└── Consumer Group: flink-processors (Apache Flink)
    ├── JDBC Sink: Writes orders to PostgreSQL
    └── Redis Sink: Updates real-time metrics (windowed aggregation)
```

---

## Real-Time Metrics (v2 and v3)

Both v2 and v3 maintain real-time metrics in Redis using the same key structure (with version prefix).

### v2 Metrics (stream-worker)

The stream-worker updates these Redis keys after each PostgreSQL write:

```
v2:metrics:total_orders   → Total order count
v2:metrics:total_revenue  → Total revenue (in cents)
v2:metrics:drink_counts   → Hash with counts per drink type
v2:metrics:drink_revenue  → Hash with revenue per drink type (in cents)
v2:metrics:store_counts   → Hash with counts per store
v2:metrics:store_revenue  → Hash with revenue per store (in cents)
```

### v3 Metrics (Flink)

The Flink job maintains these Redis keys via windowed aggregation:

```
v3:metrics:total_orders   → Total order count
v3:metrics:total_revenue  → Total revenue (in cents)
v3:metrics:drink_counts   → Hash with counts per drink type
v3:metrics:drink_revenue  → Hash with revenue per drink type (in cents)
v3:metrics:store_counts   → Hash with counts per store
v3:metrics:store_revenue  → Hash with revenue per store (in cents)
```

**Operations used (both versions):**

- `INCR/INCRBY` - Atomic counter increments
- `HINCRBY` - Atomic hash field increments (for breakdown by drink/store)
- Pipeline/transaction for atomicity

---

## Testing Each Version

### Start All Services

```bash
docker compose up -d
```

### Test v1 (Direct - Batch)

```bash
curl -X POST http://localhost:8005/api/v1/order \
  -H "Content-Type: application/json" \
  -d '{"drink":"cappuccino","store":"downtown","price":4.50,"timestamp":"2025-01-15T10:00:00Z"}'

# Dashboard updates after aggregator runs (10-60s)
```

### Test v2 (Pub/Sub - Batch)

```bash
curl -X POST http://localhost:8005/api/v2/order \
  -H "Content-Type: application/json" \
  -d '{"drink":"latte","store":"uptown","price":5.00,"timestamp":"2025-01-15T10:00:00Z"}'

# Dashboard updates after aggregator runs (10-60s)
```

### Test v3 (Kafka - Real-Time)

```bash
curl -X POST http://localhost:8005/api/v3/order \
  -H "Content-Type: application/json" \
  -d '{"drink":"americano","store":"central","price":3.50,"timestamp":"2025-01-15T10:00:00Z"}'

# Dashboard updates immediately (~100ms)!
```

---

## Architecture Files

### v3 Real-Time Components

**Flink Job (Java/Maven):**

```
flink/coffee-rt-flink/
├── pom.xml                                    # Maven build with Flink dependencies
├── Dockerfile                                 # Multi-stage build
└── src/main/java/com/coffeert/
    ├── CoffeeOrderJob.java                   # Main Flink streaming job
    ├── model/
    │   └── CoffeeOrder.java                  # Order POJO
    ├── function/
    │   └── OrderAggregator.java              # Windowed aggregation logic
    └── sink/
        └── RedisMetricsSink.java             # Custom Redis sink
```

**Helm subchart:**

```
helm/coffee-rt/charts/flink/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── configmap.yaml              # Flink configuration
    ├── jobmanager-deployment.yaml  # JobManager pod
    ├── jobmanager-service.yaml     # JobManager service
    ├── taskmanager-deployment.yaml # TaskManager pod
    ├── job-deployment.yaml         # Job submission pod
    └── _helpers.tpl
```

---

## Why v2/v3 Don't Need the Cron Aggregator

| Aggregator (Cron)  | v2 (stream-worker)             | v3 (Flink)                         |
| ------------------ | ------------------------------ | ---------------------------------- |
| Queries PostgreSQL | Consumes from Redis Stream     | Consumes from Kafka                |
| Runs every 10-60s  | Processes each message         | Processes each message immediately |
| Full table scans   | Incremental updates            | Incremental updates                |
| Overwrites Redis   | Atomic increments in Redis     | Atomic increments in Redis         |
| Single-threaded    | Consumer groups (scalable)     | Distributed, scalable              |

For v2 and v3, you can disable the cron aggregator entirely since real-time metrics are updated by the stream processors. The cron aggregator is still useful for:

- Reconciliation (correcting drift from failures)
- Historical recomputation
- v1 orders (which use direct PostgreSQL writes)
