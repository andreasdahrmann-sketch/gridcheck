"""add monetization and analysis history tables

Revision ID: 20260511_01
Revises: 20260510_01
Create Date: 2026-05-11 21:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260511_01"
down_revision = "20260510_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("plan_tier", sa.String(), nullable=False, server_default="free"))
    op.add_column("users", sa.Column("billing_status", sa.String(), nullable=False, server_default="free"))
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("stripe_price_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("billing_current_period_end", sa.DateTime(), nullable=True))
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True)
    op.create_index("ix_users_stripe_subscription_id", "users", ["stripe_subscription_id"], unique=True)

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="interactive"),
        sa.Column("status", sa.String(), nullable=False, server_default="completed"),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("request_checksum", sa.String(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("result_checksum", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("decision_code", sa.String(), nullable=True),
        sa.Column("revision_hash", sa.String(), nullable=True),
        sa.Column("billing_category", sa.String(), nullable=False, server_default="free"),
        sa.Column("free_quota_consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_runs_id", "analysis_runs", ["id"], unique=False)
    op.create_index("ix_analysis_runs_user_id", "analysis_runs", ["user_id"], unique=False)
    op.create_index("ix_analysis_runs_project_id", "analysis_runs", ["project_id"], unique=False)
    op.create_index("ix_analysis_runs_revision_hash", "analysis_runs", ["revision_hash"], unique=False)
    op.create_index(
        "ix_analysis_runs_user_created",
        "analysis_runs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_runs_project_created",
        "analysis_runs",
        ["project_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "billing_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False, server_default="stripe"),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("provider_event_id", sa.String(), nullable=True),
        sa.Column("checkout_session_id", sa.String(), nullable=True),
        sa.Column("provider_customer_id", sa.String(), nullable=True),
        sa.Column("provider_subscription_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="received"),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_billing_provider_event"),
    )
    op.create_index("ix_billing_events_id", "billing_events", ["id"], unique=False)
    op.create_index("ix_billing_events_user_id", "billing_events", ["user_id"], unique=False)
    op.create_index("ix_billing_events_checkout_session_id", "billing_events", ["checkout_session_id"], unique=False)
    op.create_index("ix_billing_events_provider_customer_id", "billing_events", ["provider_customer_id"], unique=False)
    op.create_index(
        "ix_billing_events_provider_subscription_id",
        "billing_events",
        ["provider_subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_events_user_created",
        "billing_events",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_billing_events_user_created", table_name="billing_events")
    op.drop_index("ix_billing_events_provider_subscription_id", table_name="billing_events")
    op.drop_index("ix_billing_events_provider_customer_id", table_name="billing_events")
    op.drop_index("ix_billing_events_checkout_session_id", table_name="billing_events")
    op.drop_index("ix_billing_events_user_id", table_name="billing_events")
    op.drop_index("ix_billing_events_id", table_name="billing_events")
    op.drop_table("billing_events")

    op.drop_index("ix_analysis_runs_project_created", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_user_created", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_revision_hash", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_project_id", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_user_id", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")

    op.drop_index("ix_users_stripe_subscription_id", table_name="users")
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "billing_current_period_end")
    op.drop_column("users", "stripe_price_id")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "billing_status")
    op.drop_column("users", "plan_tier")
