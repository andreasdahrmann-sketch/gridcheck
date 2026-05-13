"""add ops followup workflow fields

Revision ID: 20260512_01
Revises: 20260511_02
Create Date: 2026-05-12 13:55:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260512_01"
down_revision = "20260511_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_entitlements", sa.Column("ops_assignee_user_id", sa.Integer(), nullable=True))
    op.add_column("billing_entitlements", sa.Column("ops_assigned_at", sa.DateTime(), nullable=True))
    op.add_column("billing_entitlements", sa.Column("ops_started_at", sa.DateTime(), nullable=True))
    op.add_column("billing_entitlements", sa.Column("ops_completed_at", sa.DateTime(), nullable=True))
    op.add_column("billing_entitlements", sa.Column("ops_last_comment", sa.Text(), nullable=True))
    op.create_index(
        "ix_billing_entitlements_ops_assignee_user_id",
        "billing_entitlements",
        ["ops_assignee_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_billing_entitlements_ops_assignee_user_id",
        "billing_entitlements",
        "users",
        ["ops_assignee_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_billing_entitlements_ops_assignee_user_id",
        "billing_entitlements",
        type_="foreignkey",
    )
    op.drop_index("ix_billing_entitlements_ops_assignee_user_id", table_name="billing_entitlements")
    op.drop_column("billing_entitlements", "ops_last_comment")
    op.drop_column("billing_entitlements", "ops_completed_at")
    op.drop_column("billing_entitlements", "ops_started_at")
    op.drop_column("billing_entitlements", "ops_assigned_at")
    op.drop_column("billing_entitlements", "ops_assignee_user_id")
