


# V1

## Baseline throughput test

```
 locust -f backend/coffee_consumer_simulator/src/coffee_consumer_simulator/locustfile.py \
    --host http://localhost:8005 \
    --api-version v1 \
    --headless \
    --users 500 \
    --run-time 10m \
    --csv=results/v1-baseline

```
