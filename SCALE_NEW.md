# V2 vs V3 Performance Comparison

## Architecture Overview

**V2: Redis Streams + Python Worker**
```
API → Redis Stream (XADD) → stream-worker (Python) → PostgreSQL + Redis metrics
```

**V3: Kafka + Apache Flink**
```
API → Kafka topic → Flink JobManager → Flink TaskManagers → PostgreSQL + Redis metrics
```

## V3 Outperforms V2 When:

### 1. High throughput (>1000 orders/sec)
- V2's single Python process becomes CPU-bound
- V3 scales horizontally with multiple Flink TaskManagers processing 4+ Kafka partitions in parallel

### 2. Exactly-once semantics are required
- V2 is at-least-once (can duplicate orders on failure)
- V3 guarantees exactly-once via Flink checkpointing + `INSERT...ON CONFLICT` deduplication
- Critical for billing accuracy

### 3. Failure recovery is critical
- V2: Replays from last ACK, Redis persistence is volatile
- V3: Savepoints restore exact state, Kafka provides durable message persistence

### 4. Complex aggregations needed
- V3 can leverage Flink's windowing, sessionization, pattern detection, multi-stream joins

### 5. Multi-datacenter/high-availability deployments
- Kafka natively supports replication across datacenters

## V2 Remains Better When:

- Throughput < 500 orders/sec
- Simpler operations preferred (2 services vs 5+)
- Lower resource footprint needed (~200MB vs ~3GB+)
- Faster development iteration (Python vs Java/Flink JARs)

## Key Differences

| Aspect | V2 (Redis Streams) | V3 (Kafka + Flink) |
|--------|-------------------|-------------------|
| **Consumer Model** | Single process (Python) | Distributed cluster (Flink) |
| **Scaling** | Vertical only | Horizontal (add TaskManagers) |
| **Parallelism** | Single thread per stream | 4+ parallel tasks (configurable) |
| **Batching** | Python-level batching (100 orders or 2s) | Flink-level windowing (1s windows) |
| **State Management** | None (stream is state) | Checkpointing (fault tolerance) |
| **Exactly-once** | No (at-least-once) | Yes (Flink checkpoints + message dedup) |
| **Failure Recovery** | Consumer group replays from last ACK | Savepoints restore exact state |
| **Message Persistence** | Redis (volatile) | Kafka (durable, replicated) |

## The Crossover Point

The architecture is designed to show where v2 "breaks" - roughly **500-1000 orders/sec** is where v3's distributed processing overhead becomes worthwhile. Below that, v2's simplicity wins. Above that, v3's horizontal scalability and exactly-once guarantees justify the added complexity.

## Resource Comparison

| Metric | V2 | V3 |
|--------|----|----|
| **Memory** | ~200MB total | ~3GB+ |
| **Services** | 2 (Python worker + Redis) | 5+ (Kafka, JobManager, TaskManagers, Redis) |
| **API Response Time** | ~2-5ms | ~5-10ms |
| **Max Orders/Second** | Limited by single Python process | Scales with TaskManager count |
