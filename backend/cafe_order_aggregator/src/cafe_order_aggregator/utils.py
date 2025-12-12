"""Aggregation logic for computing metrics."""

from collections import Counter

from shared import CoffeeOrder


def compute_hourly_metrics(orders: list[CoffeeOrder]) -> dict:
    """Compute metrics for a given hour's orders.

    Args:
        orders: List of orders for the hour

    Returns:
        Dictionary with top_drinks, revenue, and order_count
    """
    if not orders:
        return {
            "top_drinks": [],
            "revenue": 0.0,
            "order_count": 0,
        }

    drink_counts = Counter(order.drink.value for order in orders)
    top_drinks = [drink for drink, _ in drink_counts.most_common(5)]
    revenue = sum(order.price for order in orders)

    return {
        "top_drinks": top_drinks,
        "revenue": round(revenue, 2),
        "order_count": len(orders),
    }


def compute_top5_drinks(orders: list[CoffeeOrder]) -> list[str]:
    """Compute top 5 drinks from orders.

    Args:
        orders: List of orders to analyze

    Returns:
        List of top 5 drink names by order count
    """
    if not orders:
        return []

    drink_counts = Counter(order.drink.value for order in orders)
    return [drink for drink, _ in drink_counts.most_common(5)]


def serialize_orders(orders: list[CoffeeOrder]) -> list[dict]:
    """Serialize orders to JSON-serializable format.

    Args:
        orders: List of orders

    Returns:
        List of order dictionaries
    """
    return [
        {
            "id": order.id,
            "drink": order.drink.value,
            "store": order.store.value,
            "price": order.price,
            "timestamp": order.timestamp.isoformat(),
        }
        for order in orders
    ]
