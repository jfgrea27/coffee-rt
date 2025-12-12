"""Main entry point for cafe order aggregator."""

import asyncio

from shared.logger import setup_logging

from cafe_order_aggregator.aggregator import run_aggregation
from cafe_order_aggregator.env import LOG_FILE

setup_logging(LOG_FILE)


def main() -> None:
    """CLI entry point."""
    asyncio.run(run_aggregation())


if __name__ == "__main__":
    main()
