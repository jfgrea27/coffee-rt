"""
Benchmark Load Tests for Coffee-RT v1, v2, v3 architectures:

Mixed workload test that simulates realistic usage:
- 70% order creation (writes)
- 20% dashboard reads
- 10% end-to-end latency measurement (order -> dashboard)

Usage:
    locust -f benchmark.py --host http://localhost:8005 --api-version v1 --headless -u 100 -r 100
"""

import random
import time
from datetime import UTC, datetime

from locust import HttpUser, LoadTestShape, between, events, task


@events.init_command_line_parser.add_listener
def add_custom_arguments(parser):
    """Add custom command line arguments."""
    parser.add_argument(
        "--api-version",
        type=str,
        default="v1",
        choices=["v1", "v2", "v3"],
        help="API version to test (v1=direct DB, v2=Redis Streams, v3=Kafka+Flink)",
    )
    parser.add_argument(
        "--breakpoint-mode",
        action="store_true",
        default=False,
        help="Enable breakpoint mode: progressively increase load until 10%% failure rate",
    )
    parser.add_argument(
        "--breakpoint-start",
        type=int,
        default=10,
        help="Starting number of users for breakpoint test (default: 10)",
    )
    parser.add_argument(
        "--breakpoint-step",
        type=int,
        default=10,
        help="Users to add each step in breakpoint test (default: 10)",
    )
    parser.add_argument(
        "--breakpoint-interval",
        type=int,
        default=15,
        help="Seconds between load increases in breakpoint test (default: 15)",
    )
    parser.add_argument(
        "--breakpoint-max",
        type=int,
        default=500,
        help="Maximum users before stopping breakpoint test (default: 500)",
    )
    parser.add_argument(
        "--breakpoint-threshold",
        type=float,
        default=0.10,
        help=(
            "HTTP error rate threshold 0-1 to stop test (default: 0.10 = 10%%). "
            "Only counts HTTP 4xx/5xx, not e2e timeouts."
        ),
    )
    parser.add_argument(
        "--warmup-timeout",
        type=int,
        default=60,
        help="Max seconds to wait for system to be ready before starting load test (default: 60)",
    )


DRINKS = ["cappuccino", "americano", "latte"]
STORES = ["uptown", "downtown", "central", "southend"]
PRICE_RANGES = {
    "cappuccino": (4.50, 6.50),
    "americano": (3.00, 4.50),
    "latte": (4.00, 6.00),
}

# Track HTTP errors separately from other failures (e.g., e2e timeouts)
http_error_count = 0
http_total_count = 0
system_ready = False  # Flag to indicate system is warmed up


@events.request.add_listener
def track_http_errors(
    name,
    exception,
    response=None,
):
    """Track HTTP 4xx/5xx errors separately from other failures."""
    global http_error_count, http_total_count
    # Don't count errors until system is ready (warmup complete)
    if not system_ready:
        return
    # Only count core requests for breakpoint calculation (exclude e2e variants)
    # This gives a cleaner signal for when the system is actually failing
    core_requests = (
        "GET /api/dashboard",
        "POST /api/v1/order",
        "POST /api/v2/order",
        "POST /api/v3/order",
    )
    if name in core_requests:
        http_total_count += 1
        # Check for HTTP error status codes (4xx/5xx) or exceptions
        if exception is not None:
            http_error_count += 1
        elif response is not None and response.status_code >= 400:
            http_error_count += 1


def create_order() -> dict:
    """Create a random order payload."""
    drink = random.choice(DRINKS)
    store = random.choice(STORES)
    price_min, price_max = PRICE_RANGES[drink]
    return {
        "drink": drink,
        "store": store,
        "price": round(random.uniform(price_min, price_max), 2),
        "timestamp": datetime.now(UTC).isoformat(),
    }


class MixedWorkloadUser(HttpUser):
    """
    Mixed workload user - simulates realistic traffic pattern.

    Workload distribution:
    - 70% order creation (writes to API)
    - 20% dashboard reads (reads from Redis cache)
    - 10% end-to-end latency (create order, poll dashboard until count increases)
    """

    wait_time = between(0.1, 0.5)

    @task(7)
    def create_order(self):
        """Create an order via the configured API version."""
        version = self.environment.parsed_options.api_version
        self.client.post(
            f"/api/{version}/order",
            json=create_order(),
            name=f"POST /api/{version}/order",
        )

    @task(2)
    def read_dashboard(self):
        """Read dashboard metrics."""
        self.client.get("/api/dashboard", name="GET /api/dashboard")

    @task(1)
    def measure_e2e_latency(self):
        """
        Measure end-to-end latency: time from order creation to dashboard update.

        1. Get current order count from dashboard
        2. Create an order
        3. Poll dashboard until count increases
        4. Report the total time as e2e latency

        Note: For v1 (cron-based aggregation), this measures time until next cron run.
        For v2/v3 (stream processing), this measures actual propagation latency.
        """
        # Skip e2e measurement in breakpoint mode (focus on core load testing)
        if getattr(self.environment.parsed_options, "breakpoint_mode", False):
            return

        version = self.environment.parsed_options.api_version

        # Get initial order count
        with self.client.get(
            "/api/dashboard", name="GET /api/dashboard (e2e)", catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure("Failed to get initial dashboard")
                return
            try:
                initial_data = response.json()
                current_hour = initial_data.get("current_hour") or {}
                initial_count = current_hour.get("order_count", 0)
            except Exception:
                response.failure("Failed to parse dashboard JSON")
                return
            response.success()

        # Create order and start timing
        start_time = time.time()
        with self.client.post(
            f"/api/{version}/order",
            json=create_order(),
            name=f"POST /api/{version}/order (e2e)",
            catch_response=True,
        ) as response:
            if response.status_code not in [200, 201, 202]:
                response.failure(f"Order creation failed: {response.status_code}")
                return
            response.success()

        # Poll dashboard until count increases
        # v1 uses cron (may take 60s+), v2/v3 should be <1s
        max_wait = 30.0 if version == "v1" else 10.0
        poll_interval = 0.1
        elapsed = 0.0

        while elapsed < max_wait:
            with self.client.get(
                "/api/dashboard", name="GET /api/dashboard (e2e poll)", catch_response=True
            ) as response:
                if response.status_code == 200:
                    try:
                        data = response.json()
                        current_hour = data.get("current_hour") or {}
                        current_count = current_hour.get("order_count", 0)
                        if current_count > initial_count:
                            # Order appeared in dashboard
                            e2e_latency = (time.time() - start_time) * 1000  # Convert to ms
                            # Report as a custom metric using environment events
                            self.environment.events.request.fire(
                                request_type="E2E",
                                name=f"e2e_latency_{version}",
                                response_time=e2e_latency,
                                response_length=0,
                                exception=None,
                                context=self.context(),
                            )
                            response.success()
                            return
                    except Exception:
                        pass
                response.success()  # Don't count poll failures

            time.sleep(poll_interval)
            elapsed = time.time() - start_time

        # Timeout - order didn't appear in dashboard within max_wait
        self.environment.events.request.fire(
            request_type="E2E",
            name=f"e2e_latency_{version}_timeout",
            response_time=max_wait * 1000,
            response_length=0,
            exception=TimeoutError(f"Order not visible in dashboard after {max_wait}s"),
            context=self.context(),
        )


@events.test_start.add_listener
def on_test_start(environment):
    """Print test start info and wait for system to be ready."""
    import requests

    global system_ready

    print(f"\n{'=' * 60}")
    print(f"Mixed Workload Benchmark - API {environment.parsed_options.api_version}")
    print("Workload: 70% orders, 20% dashboard, 10% e2e latency")
    print(f"{'=' * 60}\n")

    # Wait for system to be ready before starting load test
    host = environment.host.rstrip("/")
    max_wait = getattr(environment.parsed_options, "warmup_timeout", 60)
    check_interval = 2  # seconds
    elapsed = 0

    print(f"Waiting for system to be ready (max {max_wait}s)...")

    while elapsed < max_wait:
        try:
            # Check both readiness and dashboard endpoints
            health_resp = requests.get(f"{host}/readyz", timeout=5)
            dashboard_resp = requests.get(f"{host}/api/dashboard", timeout=5)

            if health_resp.status_code == 200 and dashboard_resp.status_code == 200:
                print(f"System ready after {elapsed}s")
                system_ready = True
                return
        except requests.exceptions.RequestException:
            pass

        time.sleep(check_interval)
        elapsed += check_interval
        print(f"  Still waiting... ({elapsed}s)")

    print(f"WARNING: System not fully ready after {max_wait}s, proceeding anyway")
    system_ready = True


@events.test_stop.add_listener
def on_test_stop(environment):
    """Print test completion info."""
    print(f"\n{'=' * 60}")
    print(f"Test completed for API {environment.parsed_options.api_version}")
    print(f"{'=' * 60}\n")


class BreakpointShape(LoadTestShape):
    """
    Progressively increase load until failure rate threshold is reached.

    This shape starts with a baseline number of users and increases
    by a fixed step every interval. It monitors the failure rate and
    stops the test when failures exceed the threshold (default 10%).

    Usage:
        locust -f benchmark.py --host http://localhost:8005 --api-version v1 \
            --headless --breakpoint-mode \
            --breakpoint-start 10 --breakpoint-step 10 --breakpoint-interval 15

    The test will output the "breaking point" - the user count at which
    the system started failing more than the threshold.
    """

    def __init__(self):
        super().__init__()
        self.current_users = 0
        self.breaking_point_users = None
        self.breaking_point_failure_rate = None
        self.last_step_time = 0

    def tick(self):  # noqa: C901
        """
        Return (user_count, spawn_rate) tuple or None to stop the test.
        Called approximately once per second by Locust.
        """
        # Get options from environment (set after init)
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._warmup_complete_time = None
            opts = self.runner.environment.parsed_options
            self.breakpoint_mode = getattr(opts, "breakpoint_mode", False)
            self.start_users = getattr(opts, "breakpoint_start", 10)
            self.step_users = getattr(opts, "breakpoint_step", 10)
            self.step_interval = getattr(opts, "breakpoint_interval", 15)
            self.max_users = getattr(opts, "breakpoint_max", 500)
            self.failure_threshold = getattr(opts, "breakpoint_threshold", 0.10)
            # Store normal mode settings
            self.normal_users = getattr(opts, "num_users", 10)
            self.normal_spawn_rate = getattr(opts, "spawn_rate", 1)

            if self.breakpoint_mode:
                self.current_users = 0  # Start with 0 users until warmup complete
                self.last_step_time = 0
                print(f"\n{'=' * 60}")
                print("BREAKPOINT TEST - Finding system limits")
                print(
                    f"Start: {self.start_users} users, Step: +{self.step_users} "
                    f"every {self.step_interval}s"
                )
                threshold_pct = self.failure_threshold * 100
                print(f"Stop at: {threshold_pct:.0f}% failure rate or {self.max_users} users")
                print(f"{'=' * 60}\n")

        # Normal mode: use -u and -r from command line
        if not self.breakpoint_mode:
            return (self.normal_users, self.normal_spawn_rate)

        # Wait for system to be ready before starting load
        if not system_ready:
            return (0, 1)  # No users until warmup complete

        # Record when warmup completed and start the test
        if self._warmup_complete_time is None:
            self._warmup_complete_time = self.get_run_time()
            self.current_users = self.start_users
            self.last_step_time = 0
            print(f"Warmup complete, starting with {self.start_users} users")

        # Use time since warmup completed for scaling decisions
        run_time = self.get_run_time() - self._warmup_complete_time

        # Calculate HTTP error percentage (excludes e2e timeouts)
        error_pct = http_error_count / http_total_count if http_total_count > 0 else 0.0

        # Check if we've hit the breaking point (error percentage exceeds threshold)
        if http_total_count > 50 and error_pct >= self.failure_threshold:
            if self.breaking_point_users is None:
                self.breaking_point_users = self.current_users
                self.breaking_point_failure_rate = error_pct
                print(f"\n{'!' * 60}")
                print("BREAKING POINT REACHED!")
                print(f"Users: {self.current_users}")
                print(f"HTTP error rate: {error_pct * 100:.1f}%")
                print(f"HTTP errors: {http_error_count} / {http_total_count}")
                print(f"{'!' * 60}\n")
            return None  # Stop the test

        # Check if we've hit max users
        if self.current_users >= self.max_users:
            print(f"\n{'=' * 60}")
            print(f"MAX USERS REACHED ({self.max_users}) - System did not break!")
            print(f"Final HTTP error rate: {error_pct * 100:.1f}%")
            print(f"{'=' * 60}\n")
            return None

        # Check if it's time to increase load
        if run_time - self.last_step_time >= self.step_interval:
            self.last_step_time = run_time
            if self.current_users < self.max_users:
                old_users = self.current_users
                self.current_users = min(self.current_users + self.step_users, self.max_users)
                print(
                    f"[{run_time:.0f}s] Scaling: {old_users} -> {self.current_users} users "
                    f"(HTTP errors: {error_pct * 100:.1f}%, requests: {http_total_count})"
                )

        # Spawn rate = step_users to ramp quickly within each step
        return (self.current_users, self.step_users)
