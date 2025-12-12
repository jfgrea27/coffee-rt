# Known Limitations & System Design Criticisms

Potential criticisms of this architecture from a system design interview perspective.

---

## Scalability Concerns

| Criticism                    | The Problem                                                                                                                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Write bottleneck**         | Every order is a synchronous INSERT to PostgreSQL. No buffering, batching, or write-behind cache. At high volume, DB becomes the chokepoint. |
| **Single writer**            | No sharding strategy. How do you scale writes beyond one PostgreSQL instance?                                                                |
| **Aggregator doesn't scale** | It's a single cron job. What if aggregation takes longer than the cron interval? Jobs pile up.                                               |
| **WebSocket fan-out**        | Multiple API pods = each has its own WebSocket connections. How do you broadcast to all clients? (Need Redis pub/sub or similar)             |

---

## Reliability Concerns

| Criticism                    | The Problem                                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| **No back-pressure**         | If PostgreSQL is slow, requests queue up unboundedly. No circuit breaker, no load shedding. |
| **Single points of failure** | One PostgreSQL, one Redis. No replicas, no failover shown.                                  |
| **No retry/DLQ for orders**  | If INSERT fails, the order is lost. No dead letter queue, no retry mechanism.               |
| **Aggregator failure**       | If cron job fails mid-run, what happens? Partial state? Stale cache forever?                |

---

## Consistency Concerns

| Criticism                | The Problem                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------- |
| **Stale dashboard data** | Dashboard is only as fresh as the last cron run (could be minutes old).             |
| **No idempotency**       | Duplicate POST = duplicate order. No idempotency key.                               |
| **Race conditions**      | Aggregator reads while API writes. Could miss orders or double-count at boundaries. |
| **Cache-DB divergence**  | Redis and PostgreSQL can drift. No consistency guarantees.                          |

---

## Operational Concerns

| Criticism                          | The Problem                                                                            |
| ---------------------------------- | -------------------------------------------------------------------------------------- |
| **No observability on aggregator** | How long does aggregation take? Is it approaching the cron interval? No metrics shown. |
| **Schema migrations**              | How do you deploy DB changes with zero downtime?                                       |
| **No graceful degradation**        | If Redis dies, does `/api/dashboard` return an error or fall back to DB?               |

---

## Design Trade-offs to Defend

These aren't "wrong" - they're trade-offs. Acknowledge them and explain:

```
"Yes, the cron-based aggregation adds latency. I chose this because:
1. Dashboard refresh is 30 seconds anyway - sub-second metrics aren't needed
2. It keeps the write path simple and fast
3. Aggregation logic is just SQL, easy to debug
4. If we needed real-time, I'd add Redis INCR for hot counters"
```

---

## Quick Wins to Address Critics

| Add This                                     | Shows You Understand   |
| -------------------------------------------- | ---------------------- |
| Idempotency key on orders                    | Distributed systems    |
| Circuit breaker (e.g., `circuitbreaker` lib) | Resilience patterns    |
| Redis pub/sub for WebSocket broadcast        | Multi-instance scaling |
| Aggregator duration metric                   | Operational awareness  |
| Graceful fallback if Redis down              | Degradation strategies |

---

## What Interviewers Are Really Testing

Interviewers don't expect a perfect system. They want to see:

1. **You know the weaknesses** - Self-awareness > perfection
2. **You can justify trade-offs** - "I chose X because Y"
3. **You know what to add next** - "If this needed to scale 10x, I'd add..."

See [BLOG.md](BLOG.md) for detailed explanations of architectural decisions.
