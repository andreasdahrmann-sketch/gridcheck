"""add conversion_events table for KPI tracking

Revision ID: 20260515_01
Revises: 20260512_03
Create Date: 2026-05-15 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260515_01"
down_revision = "20260512_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversion_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_name", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversion_events_id", "conversion_events", ["id"], unique=False)
    op.create_index("ix_conversion_events_user_id", "conversion_events", ["user_id"], unique=False)
    op.create_index("ix_conversion_events_event_name", "conversion_events", ["event_name"], unique=False)
    op.create_index("ix_conversion_events_session_id", "conversion_events", ["session_id"], unique=False)
    op.create_index(
        "ix_conversion_events_user_created",
        "conversion_events",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_conversion_events_name_created",
        "conversion_events",
        ["event_name", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversion_events_name_created", table_name="conversion_events")
    op.drop_index("ix_conversion_events_user_created", table_name="conversion_events")
    op.drop_index("ix_conversion_events_session_id", table_name="conversion_events")
    op.drop_index("ix_conversion_events_event_name", table_name="conversion_events")
    op.drop_index("ix_conversion_events_user_id", table_name="conversion_events")
    op.drop_index("ix_conversion_events_id", table_name="conversion_events")
    op.drop_table("conversion_events")
