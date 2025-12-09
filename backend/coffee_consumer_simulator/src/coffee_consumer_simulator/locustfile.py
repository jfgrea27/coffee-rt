"""
Coffee Consumer Simulator using Locust.

Simulates customers ordering different types of coffee drinks
at various store locations.
"""

import random
from datetime import UTC, datetime

from locust import HttpUser, between, task


class CoffeeConsumer(HttpUser):
    """Simulates a coffee consumer ordering drinks at different locations."""

    wait_time = between(1, 5)

    DRINKS = ["cappuccino", "americano", "latte"]
    STORES = ["uptown", "downtown", "central", "southend"]

    PRICE_RANGES = {
        "cappuccino": (4.50, 6.50),
        "americano": (3.00, 4.50),
        "latte": (4.00, 6.00),
    }

    @task(10)
    def order_random_coffee(self) -> None:
        """Order a random coffee drink at a random location."""
        drink = random.choice(self.DRINKS)
        store = random.choice(self.STORES)
        price_min, price_max = self.PRICE_RANGES[drink]
        price = round(random.uniform(price_min, price_max), 2)

        order = {
            "drink": drink,
            "store": store,
            "price": price,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.client.post("/api/order", json=order)

    @task(3)
    def order_cappuccino(self) -> None:
        """Order a cappuccino - the most popular drink."""
        store = random.choice(self.STORES)
        price_min, price_max = self.PRICE_RANGES["cappuccino"]
        price = round(random.uniform(price_min, price_max), 2)

        order = {
            "drink": "cappuccino",
            "store": store,
            "price": price,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.client.post("/api/order", json=order)

    @task(2)
    def order_morning_latte(self) -> None:
        """Order a latte - popular morning choice."""
        store = random.choice(self.STORES)
        price_min, price_max = self.PRICE_RANGES["latte"]
        price = round(random.uniform(price_min, price_max), 2)

        order = {
            "drink": "latte",
            "store": store,
            "price": price,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.client.post("/api/order", json=order)

    @task(1)
    def order_americano(self) -> None:
        """Order an americano - simple and classic."""
        store = random.choice(self.STORES)
        price_min, price_max = self.PRICE_RANGES["americano"]
        price = round(random.uniform(price_min, price_max), 2)

        order = {
            "drink": "americano",
            "store": store,
            "price": price,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.client.post("/api/order", json=order)


class DowntownRegular(HttpUser):
    """Simulates a regular customer who always orders at downtown."""

    wait_time = between(2, 8)

    DRINKS = ["cappuccino", "americano", "latte"]
    PRICE_RANGES = {
        "cappuccino": (4.50, 6.50),
        "americano": (3.00, 4.50),
        "latte": (4.00, 6.00),
    }

    @task
    def order_at_downtown(self) -> None:
        """Order coffee at downtown location."""
        drink = random.choice(self.DRINKS)
        price_min, price_max = self.PRICE_RANGES[drink]
        price = round(random.uniform(price_min, price_max), 2)

        order = {
            "drink": drink,
            "store": "downtown",
            "price": price,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.client.post("/api/order", json=order)


class CappuccinoLover(HttpUser):
    """Simulates a customer who only drinks cappuccinos."""

    wait_time = between(3, 10)

    STORES = ["uptown", "downtown", "central", "southend"]

    @task
    def order_cappuccino(self) -> None:
        """Order a cappuccino at a random location."""
        store = random.choice(self.STORES)
        price = round(random.uniform(4.50, 6.50), 2)

        order = {
            "drink": "cappuccino",
            "store": store,
            "price": price,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.client.post("/api/order", json=order)


class RushHourCustomer(HttpUser):
    """Simulates rush hour customers who order quickly."""

    wait_time = between(0.5, 2)

    DRINKS = ["cappuccino", "americano", "latte"]
    STORES = ["uptown", "downtown", "central", "southend"]
    PRICE_RANGES = {
        "cappuccino": (4.50, 6.50),
        "americano": (3.00, 4.50),
        "latte": (4.00, 6.00),
    }

    @task
    def quick_order(self) -> None:
        """Place a quick order during rush hour."""
        drink = random.choice(self.DRINKS)
        store = random.choice(self.STORES)
        price_min, price_max = self.PRICE_RANGES[drink]
        price = round(random.uniform(price_min, price_max), 2)

        order = {
            "drink": drink,
            "store": store,
            "price": price,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.client.post("/api/order", json=order)
