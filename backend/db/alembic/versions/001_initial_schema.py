"""Initial schema creation with tables and extensions.

Revision ID: 001
Revises:
Create Date: 2025-11-12

"""

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = os.environ.get("POSTGRES_SCHEMA", "coffee_rt")


def upgrade() -> None:
    # Create enum types in the application schema
    drink_enum = sa.Enum(
        "cappuccino", "americano", "latte", name="drink_type", schema=SCHEMA, create_type=True
    )
    store_enum = sa.Enum(
        "uptown",
        "downtown",
        "central",
        "southend",
        name="store_type",
        schema=SCHEMA,
        create_type=True,
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("drink", drink_enum, nullable=False),
        sa.Column("store", store_enum, nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("orders", schema=SCHEMA)
    op.execute(f"DROP TYPE {SCHEMA}.drink_type")
    op.execute(f"DROP TYPE {SCHEMA}.store_type")
