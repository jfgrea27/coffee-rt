# Design Decisions: Why This Architecture?

This document explains the architectural choices behind coffee-rt and why simpler solutions were chosen over more complex alternatives.

---

## Why No Kafka?

Kafka is the default answer for real-time data pipelines. But it comes with significant costs:

### What Kafka Adds

- **Operational complexity**: ZooKeeper (or KRaft), broker management, partition rebalancing
- **Infrastructure cost**: Minimum 3 brokers for production, significant memory/disk requirements
- **Learning curve**: Topics, partitions, consumer groups, offset management
- **Latency for small scale**: Connection overhead, batching delays

### What We Actually Need

For a coffee ordering system with metrics aggregation:

| Requirement | Kafka Solution | Simple Solution |
|-------------|---------------|-----------------|
| Durable writes | Kafka topic | PostgreSQL (already durable) |
| Metrics aggregation | Kafka Streams / ksqlDB | Cron job reading from DB |
| Real-time dashboard | Consumer polling topic | Redis cache + WebSocket |

### The Trade-off

```
Kafka Approach:
  Order → Kafka → Stream Processor → Aggregated Topic → Dashboard Consumer

  Pros: True real-time, replayable, scales to millions of events/sec
  Cons: 5+ services to manage, partition logic, exactly-once complexity

Simple Approach:
  Order → PostgreSQL → (cron) Aggregator → Redis → Dashboard

  Pros: 3 services, familiar tech, easy debugging, good enough latency
  Cons: Aggregation delay (cron interval), DB as bottleneck at scale
```

### When to Use Kafka

Kafka makes sense when you need:
- Sub-second latency at scale (>10k events/sec)
- Event replay and time-travel debugging
- Multiple independent consumers of the same stream
- Cross-datacenter replication

For a coffee shop with hundreds of orders per hour? PostgreSQL + cron is sufficient.

**The goal of this project is to find where "sufficient" breaks down.**

---

## Cron vs Streaming for Aggregation

### The Streaming Approach

In a streaming architecture, aggregations happen continuously:

```
Order Event → Stream Processor → Update Running Totals → Emit to Sink
```

Frameworks: Kafka Streams, Apache Flink, Spark Streaming, Apache Beam

**Characteristics:**
- Results available immediately (sub-second)
- Complex windowing logic (tumbling, sliding, session windows)
- State management (checkpointing, exactly-once semantics)
- Scales horizontally with partitions

### The Cron Approach (What We Use)

```
Every N minutes:
  1. Query PostgreSQL for orders in time window
  2. Compute aggregations in Python
  3. Write results to Redis
  4. Dashboard reads from Redis
```

**Characteristics:**
- Results delayed by cron interval (1-5 minutes typically)
- Simple SQL queries, no special frameworks
- State is just "last run timestamp"
- Scales vertically (bigger queries) until it doesn't

### Why Cron Works Here

| Factor | Our Case |
|--------|----------|
| Latency requirement | Dashboard refreshes every 30s anyway |
| Data volume | Hundreds/thousands of orders per hour |
| Query complexity | Simple GROUP BY aggregations |
| Operational burden | Zero - it's a cron job |

### The Breaking Point

Cron-based aggregation fails when:

1. **Volume exceeds query capacity**: If `SELECT ... GROUP BY` takes longer than the cron interval
2. **Latency matters**: If users need sub-second metric updates
3. **Complex event processing**: If you need sessionization, pattern detection, or multi-stream joins

### Hybrid Approach (Future)

A middle ground exists:

```
Writes: Order → PostgreSQL (unchanged)
Hot metrics: Order → Redis INCR (real-time counters)
Cold analytics: PostgreSQL → Cron → Redis (complex aggregations)
```

This gives real-time simple counters with batch complex analytics.

---

## PostgreSQL as the Source of Truth

### Why Not Write Directly to Redis?

Redis is fast but:
- No durable storage (RDB/AOF have trade-offs)
- No complex queries (joins, window functions)
- No transactional guarantees across keys
- Data modeling is harder (no schema)

PostgreSQL gives us:
- ACID transactions
- Rich query capability for analytics
- Familiar tooling (psql, pg_dump, migrations)
- Point-in-time recovery

### The Pattern

```
PostgreSQL: Source of truth, durable storage, complex queries
Redis: Cache layer, fast reads, pub/sub for real-time
```

This separation means:
- If Redis dies, we lose cache but not data
- If PostgreSQL is slow, Redis serves stale data gracefully
- Analytics can hit PostgreSQL directly without affecting API latency

---

## WebSocket vs Polling

### The Polling Approach

```javascript
setInterval(() => {
  fetch('/api/dashboard')
    .then(res => res.json())
    .then(updateUI)
}, 5000)
```

**Problems:**
- Wasted requests when nothing changed
- Fixed latency (always wait for interval)
- Server load scales with clients × poll frequency

### The WebSocket Approach (What We Use)

```javascript
const ws = new WebSocket('/ws/dashboard')
ws.onmessage = (event) => updateUI(JSON.parse(event.data))
```

**Benefits:**
- Server pushes only when data changes
- Lower latency (push vs poll)
- More efficient for many clients

### Trade-offs

WebSockets add complexity:
- Connection state management
- Reconnection logic
- Load balancer sticky sessions (or Redis pub/sub for multi-instance)

For a dashboard with real-time updates, the complexity is worth it.

---

## What This Project Tests

By choosing the "simple" path, we can measure:

1. **Where does PostgreSQL INSERT become the bottleneck?**
   - Connection pool exhaustion
   - Write throughput limits
   - Index maintenance overhead

2. **Where does batch aggregation break?**
   - Query execution time vs cron interval
   - Memory usage for large result sets
   - Lock contention with concurrent writes

3. **Where does Redis become the bottleneck?**
   - Connection limits
   - Memory for cached data
   - Pub/sub fan-out limits

4. **Where do WebSockets break?**
   - Connection limits per instance
   - Memory per connection
   - Broadcast latency at scale

The answers inform when to reach for Kafka, when to add read replicas, when to shard, or when the simple solution is good enough.

---

## Conclusion

Complex systems have their place. But complexity has costs:
- More things to break
- Harder to debug
- Slower to iterate
- More expensive to run

Start simple. Measure. Add complexity only when the data demands it.

This project is the "start simple" baseline. [SCALE.md](SCALE.md) documents where it breaks.
