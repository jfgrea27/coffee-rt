# Architecture Improvement Ideas

## Current Capacity Estimate

### Bottleneck Analysis

| Component | Bottleneck | Estimated Limit |
|-----------|-----------|-----------------|
| **Order writes** | Sync INSERT + COMMIT per request | ~500-2,000 orders/sec |
| **Aggregator** | Loads ALL 30-day orders into memory | Breaks at ~500K orders |
| **WebSocket** | No pub/sub, single-instance broadcast | ~500-1,000 connections |
| **PostgreSQL** | Single primary, no pooling config | ~5,000 TPS |
| **Redis** | Standalone, no clustering | ~50,000 ops/sec (not the bottleneck) |

### Realistic User Capacity

**Conservative estimate: 50-200 concurrent users**

Here's the math:
- If each user places 1 order every 2 minutes = 0.5 orders/sec per user
- 200 users = 100 orders/sec (well within write capacity)
- Dashboard polling = 200 WebSocket connections (fine)
- After 1 week at 100 orders/sec: **~60M orders** → aggregator query explodes

**The real killer is `get_orders_last_30_days()`** in `cafe_order_aggregator/db/queries.py`:
```python
# This fetches EVERY order from 30 days into Python memory
rows = await cur.fetchall()  # OOM at scale
```

At 1,000 orders/hour for 30 days = **720,000 rows loaded every 10 seconds**.

---

## Should We Use Kafka?

**Short answer: Not yet.**

### When Kafka Makes Sense
- **Event sourcing**: You need to replay events, multiple consumers
- **Decoupling at scale**: Multiple services consuming the same event stream
- **Guaranteed ordering**: Strict order of events matters
- **Throughput > 50,000 events/sec**: Beyond what PostgreSQL handles well

### Current Situation
We have a **single writer** (API) and a **single reader** (aggregator). Kafka adds operational complexity (Zookeeper/KRaft, brokers, schema registry, consumer groups) without solving the actual bottleneck.

### Alternatives to Kafka

| Technology | Use Case | Complexity |
|------------|----------|------------|
| **PostgreSQL LISTEN/NOTIFY** | Simple pub/sub, <1000 events/sec | Low |
| **Redis Streams** | Lightweight event log, consumer groups | Medium |
| **AWS SQS/SNS** | Managed queue, no infra | Low |
| **Kafka** | High throughput, multiple consumers, replay | High |

### When to Graduate to Kafka

Consider Kafka when:
- Multiple consumers needed (analytics service, ML pipeline, audit log)
- Hitting 10,000+ orders/sec sustained
- Need exactly-once processing guarantees
- Need replay capability for reprocessing

---

## Quick Wins (Low Effort, High Impact)

### 1. Fix the Aggregator Query (30 min, huge impact)

Instead of loading 720K rows into Python:
```sql
SELECT drink, COUNT(*) as count
FROM coffee_rt.orders
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY drink
ORDER BY count DESC
LIMIT 5;
```
This returns 3-5 rows instead of 720,000.

### 2. Enable HPA for the API (already configured)

```yaml
# helm/coffee-rt/charts/api/values.yaml
autoscaling:
  enabled: true  # Currently false
  minReplicas: 2
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
```

### 3. Add Connection Pooling Limits

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)
```

### 4. Add Rate Limiting

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/order")
@limiter.limit("100/minute")
async def create_order(...):
```

---

## Medium Effort Improvements

### 1. Database Resilience

**Add PostgreSQL Read Replicas**
```yaml
postgresql:
  architecture: replication
  readReplicas:
    replicaCount: 2
```
Route aggregator and dashboard queries to replicas.

**Partition the Orders Table**
```sql
CREATE TABLE coffee_rt.orders (
    id SERIAL,
    drink coffee_rt.drink NOT NULL,
    store coffee_rt.store NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

CREATE TABLE coffee_rt.orders_2025_01 PARTITION OF coffee_rt.orders
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

**Add Composite Index**
```sql
CREATE INDEX ix_orders_timestamp_drink_store
ON coffee_rt.orders (timestamp, drink, store);
```

### 2. Redis High Availability

**Switch to Sentinel**
```yaml
redis:
  architecture: sentinel
  sentinel:
    enabled: true
    masterSet: coffee-rt-master
  replica:
    replicaCount: 2
```

**Add Cache Stampede Protection**
```python
async def get_cached_metrics(key: str):
    value = await redis.get(key)
    if value:
        return json.loads(value)

    async with redis.lock(f"lock:{key}", timeout=5):
        value = await redis.get(key)
        if value:
            return json.loads(value)

        result = await compute_metrics()
        await redis.setex(key, TTL, json.dumps(result))
        return result
```

### 3. Circuit Breakers

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
async def get_db_connection():
    return await engine.connect()

@circuit(failure_threshold=5, recovery_timeout=30)
async def get_redis_connection():
    return await redis_pool.get_connection()
```

### 4. Decouple Order Ingestion (Write Buffer)

Current flow: `API → PostgreSQL` (synchronous, blocking)

Better: `API → Redis Queue → Worker → PostgreSQL`

```python
# In order endpoint
@app.post("/api/order")
async def create_order(order: CoffeeOrder):
    await redis.rpush("orders:pending", order.model_dump_json())
    orders_created_total.labels(drink=order.drink, store=order.store).inc()
    return {"status": "accepted"}

# New worker process
async def order_writer():
    while True:
        order_json = await redis.blpop("orders:pending", timeout=1)
        if order_json:
            order = CoffeeOrder.model_validate_json(order_json)
            await db.execute(insert(Order).values(...))
```

---

## Higher Effort Improvements

### 1. Aggregator Improvements

**Adaptive Scheduling**
```python
last_run_duration = 0

async def run_aggregation():
    global last_run_duration
    start = time.time()
    await aggregate()
    last_run_duration = time.time() - start

    sleep_time = max(10, last_run_duration * 2)
    await asyncio.sleep(sleep_time)
```

**Incremental Aggregation**
```python
last_processed = await redis.get("aggregator:last_processed")
new_orders = await db.execute(
    select(Order).where(Order.timestamp > last_processed)
)
# Update running totals instead of full recalculation
```

**Materialized Views**
```sql
CREATE MATERIALIZED VIEW coffee_rt.hourly_metrics AS
SELECT
    date_trunc('hour', timestamp) as hour,
    drink,
    store,
    COUNT(*) as order_count,
    SUM(price) as revenue
FROM coffee_rt.orders
GROUP BY 1, 2, 3;

CREATE UNIQUE INDEX ON coffee_rt.hourly_metrics (hour, drink, store);

REFRESH MATERIALIZED VIEW CONCURRENTLY coffee_rt.hourly_metrics;
```

### 2. WebSocket Scaling

**Pub/Sub for Multi-Instance**
```python
async def broadcast_update(data: dict):
    await redis.publish("dashboard:updates", json.dumps(data))

async def listen_for_updates():
    pubsub = redis.pubsub()
    await pubsub.subscribe("dashboard:updates")
    async for message in pubsub.listen():
        for ws in connected_websockets:
            await ws.send_json(message["data"])
```

**Chunked Updates (send only diffs)**
```python
previous_state = {}

async def broadcast_diff(new_state: dict):
    diff = {k: v for k, v in new_state.items()
            if previous_state.get(k) != v}
    if diff:
        await broadcast(diff)
    previous_state.update(new_state)
```

### 3. Observability

**Add Distributed Tracing**
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

FastAPIInstrumentor.instrument_app(app)
AsyncPGInstrumentor().instrument()
RedisInstrumentor().instrument()
```

---

## Priority Matrix

| Change | Effort | Impact | Priority |
|--------|--------|--------|----------|
| Fix aggregator queries (push to SQL) | Low | **Very High** | Do Now |
| Enable HPA | Low | High | Do Now |
| Connection pool limits | Low | Medium | Do Now |
| Rate limiting | Low | High | Do Now |
| Circuit breakers | Medium | High | Soon |
| Redis Sentinel | Medium | High | Soon |
| Read replicas | Medium | High | Soon |
| Write buffer (Redis queue) | Medium | High | Soon |
| Table partitioning | Medium | Medium | Later |
| Distributed tracing | Medium | Medium | Later |
| Incremental aggregation | High | High | Later |
| Materialized views | High | High | Later |

---

## Expected Capacity After Fixes

After implementing quick wins:
- **1,000-5,000 concurrent users**
- **5,000-10,000 orders/sec** write capacity
- **Aggregator handling 10M+ orders** without OOM

Only consider Kafka after hitting these limits with the "boring stack."
