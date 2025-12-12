# Load Testing Experiments

Load testing experiments for the coffee ordering system.

---

## 1. Baseline Throughput Tests

| Experiment                           | What to Measure                        |
| ------------------------------------ | -------------------------------------- |
| Ramp up users 10→100→500 over 10 min | Max orders/sec before latency degrades |
| Sustained load at 80% capacity       | P95/P99 latency stability              |

```bash
locust -f backend/coffee_consumer_simulator/src/coffee_consumer_simulator/locustfile.py \
  --users 200 --spawn-rate 10 --run-time 5m
```

---

## 2. Spike Testing

Simulate sudden traffic bursts (e.g., morning rush):

- Start with 50 users → spike to 500 in 30 seconds → hold 2 min → drop back
- **Observe**: Does the system recover? Any request queuing? DB connection pool exhaustion?

---

## 3. Database Stress Tests

| Experiment                                | Goal                               |
| ----------------------------------------- | ---------------------------------- |
| High write volume (RushHourCustomer only) | Test PostgreSQL insert performance |
| Concurrent reads during aggregator run    | Check for lock contention          |
| Connection pool limits                    | Verify pool exhaustion behavior    |

---

## 4. Redis Cache Effectiveness

- Run load test while aggregator is **disabled** vs **running**
- Measure `/api/dashboard` latency with cold cache vs warm cache
- Test cache invalidation under high write load

---

## 5. WebSocket Connection Limits

- Open 100→500→1000 concurrent WebSocket connections
- **Measure**: Memory usage, connection failures, broadcast latency
- Test reconnection behavior after pod restart

---

## 6. Failure Injection Tests

| Scenario                             | Expected Behavior                              |
| ------------------------------------ | ---------------------------------------------- |
| Kill Redis mid-test                  | API should fail gracefully, health check fails |
| Kill PostgreSQL                      | Orders fail, `/readyz` returns unhealthy       |
| Network latency injection (tc netem) | Test timeout handling                          |
| Aggregator fails during computation  | Stale cache served                             |

---

## 7. Endurance/Soak Test

- Run 100 users for 2-4 hours
- **Watch for**: Memory leaks, connection leaks, database growth, metric cardinality explosion

---

## 8. Mixed Workload Ratios

Test different traffic patterns using existing user profiles:

```python
# In locustfile.py, adjust weights:
class CoffeeConsumer(HttpUser):
    weight = 10  # baseline

class RushHourCustomer(HttpUser):
    weight = 5   # high frequency

class DowntownRegular(HttpUser):
    weight = 3   # store-specific
```

---

## 9. Aggregator Under Pressure

- Fill database with 1M+ orders, then run aggregator
- Measure: Query execution time, Redis write latency, memory usage
- Test with concurrent API load during aggregation

---

## 10. Prometheus Metrics Cardinality

- High store/drink combination diversity
- Check if `orders_created_total` labels cause memory issues

---

## Implementation Priorities

1. **Add a spike test profile** to locustfile
2. **Create a soak test script** that runs overnight
3. **Add Grafana dashboards** to correlate Locust metrics with Prometheus
4. **Test k8s HPA scaling** under load (if configured)
