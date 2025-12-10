"""Add indexes to orders table for query performance.

Revision ID: 002
Revises: 001
Create Date: 2025-12-10

"""

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = os.environ.get("POSTGRES_SCHEMA", "coffee_rt")


def upgrade() -> None:
    # Index on timestamp for time-based queries (recent orders, hourly metrics)
    op.create_index(
        "ix_orders_timestamp",
        "orders",
        ["timestamp"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_orders_timestamp", table_name="orders", schema=SCHEMA)
