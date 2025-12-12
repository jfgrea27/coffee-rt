"""Add message_id column for stream-worker idempotency.

Revision ID: 003
Revises: 002
Create Date: 2025-12-11

"""

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = os.environ.get("POSTGRES_SCHEMA", "coffee_rt")


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("message_id", sa.String(length=255), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_orders_message_id",
        "orders",
        ["message_id"],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_orders_message_id", table_name="orders", schema=SCHEMA)
    op.drop_column("orders", "message_id", schema=SCHEMA)
