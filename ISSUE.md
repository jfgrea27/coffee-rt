# Production Readiness Issues

## Critical Issues

### Database & Scaling
- [ ] Single shared DB connection across all requests - will fail at ~10 concurrent users (`app.py:54`)
- [ ] No connection pooling configured
- [ ] No prepared statements validation
- [ ] Missing indexes on `timestamp` for time-range queries

### Error Handling & Resilience
- [ ] No timeouts on DB/Redis connections (can hang forever)
- [ ] Broad `except Exception` catching without specific error handling (`app.py:58-72`)
- [ ] API has no retry logic (aggregator does have it)
- [ ] WebSocket connections can hang indefinitely - no max timeout
- [ ] No circuit breaker pattern

### Security
- [ ] No authentication/authorization - API completely open
- [ ] WebSocket broadcasts to all clients without auth
- [ ] Hardcoded credentials in config (default password `coffee-rt_password`)
- [ ] No rate limiting - vulnerable to DoS
- [ ] No CORS configuration
- [ ] Secrets exposed in error logs
- [ ] No HTTPS/TLS enforcement in Kubernetes configs
- [ ] No dependency vulnerability scanning

### Concurrency & State Management
- [ ] Race conditions: multiple WebSocket handlers share `app.state.redis_connection` without locks (`app.py:184`)
- [ ] Mutable shared state across requests
- [ ] No connection pooling in WebSocket loop

## High Priority Issues

### Data Validation
- [ ] Negative prices accepted - Pydantic doesn't validate by default (`test_api_order.py:226`)
- [ ] No input sanitization on JSON from Redis/cache (`dashboard.py:30-35`)
- [ ] Enum deserialization without validation (`aggregator/db/queries.py:40-41`)

### Testing Gaps
- [ ] Tests heavily mocked - minimal real integration testing
- [ ] No WebSocket load/concurrent connection testing
- [ ] No database transaction testing
- [ ] No performance/load tests in CI despite Locust being added
- [ ] Frontend tests minimal - no WebSocket integration tests

### Observability
- [ ] No metrics collection (Prometheus, etc.)
- [ ] No distributed tracing or correlation IDs
- [ ] No alerting rules or monitoring dashboards
- [ ] Logging has hardcoded file path (`logger.py:109` - `logs/trader.log`)

### Infrastructure & Deployment
- [ ] CI/CD has `push: false` - never actually pushes images to registry (`ci.yaml:251`)
- [ ] Helm charts incomplete:
  - Resource limits too low (128Mi request, 512Mi limit)
  - No persistence volumes for stateful services
  - No database/Redis subcharts
  - Autoscaling disabled by default
  - No network policies
- [ ] No rollback strategy or canary deployments
- [ ] Docker images not optimized (no multi-stage builds for aggregator)

## Medium Priority Issues

### Bugs
- [ ] Aggregator has `main()` called twice (`aggregator/main.py:136-137`)
- [ ] Dashboard endpoint uses `datetime.now().hour` which can change during request

### Cache & State
- [ ] Redis data has no version/schema contract
- [ ] TTL mismatches - hourly data expires in 25 hours, top5 drinks never expire (`aggregator.py:84-85, 97`)
- [ ] Recent orders expire after 2 hours but updated hourly - staleness undefined

### API Design
- [ ] No API versioning
- [ ] No request tracing headers (X-Request-ID)
- [ ] No graceful shutdown / connection draining

### Type Safety
- [ ] Frontend hooks lack proper error typing
- [ ] No ConfigMap for feature flags

## Summary

| Category | Impact | Effort |
|----------|--------|--------|
| No connection pooling | Fails at <10 users | High |
| No timeouts | Infinite hangs | Medium |
| No authentication | Completely open API | High |
| Shared unprotected state | Race conditions | Medium |
| No load/integration tests | Can't validate scalability | High |
| Incomplete CI/CD | Can't deploy to production | High |
| Zero metrics/alerting | Blind in production | High |

**Bottom line**: This is a working proof-of-concept but would fail immediately under production load.
