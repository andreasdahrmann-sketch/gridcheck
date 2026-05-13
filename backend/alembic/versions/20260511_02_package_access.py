"""add package entitlements and analysis package fields

Revision ID: 20260511_02
Revises: 20260511_01
Create Date: 2026-05-11 21:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260511_02"
down_revision = "20260511_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_entitlements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.String(), nullable=False),
        sa.Column("offer_category", sa.String(), nullable=False, server_default="pay_per_use"),
        sa.Column("package_scope", sa.String(), nullable=False, server_default="basic"),
        sa.Column("source", sa.String(), nullable=False, server_default="checkout"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("total_credits", sa.Integer(), nullable=True),
        sa.Column("used_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("checkout_session_id", sa.String(), nullable=True),
        sa.Column("stripe_price_id", sa.String(), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("express_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ops_followup_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ops_status", sa.String(), nullable=False, server_default="not_required"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_entitlements_id", "billing_entitlements", ["id"], unique=False)
    op.create_index("ix_billing_entitlements_user_id", "billing_entitlements", ["user_id"], unique=False)
    op.create_index("ix_billing_entitlements_offer_id", "billing_entitlements", ["offer_id"], unique=False)
    op.create_index(
        "ix_billing_entitlements_checkout_session_id",
        "billing_entitlements",
        ["checkout_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_entitlements_stripe_subscription_id",
        "billing_entitlements",
        ["stripe_subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_entitlements_user_status",
        "billing_entitlements",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_billing_entitlements_user_offer",
        "billing_entitlements",
        ["user_id", "offer_id"],
        unique=False,
    )

    op.add_column("analysis_runs", sa.Column("offer_id", sa.String(), nullable=True))
    op.add_column("analysis_runs", sa.Column("package_scope", sa.String(), nullable=False, server_default="basic"))
    op.add_column("analysis_runs", sa.Column("usage_bucket", sa.String(), nullable=False, server_default="free"))
    op.add_column("analysis_runs", sa.Column("entitlement_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_analysis_runs_entitlement_id",
        "analysis_runs",
        "billing_entitlements",
        ["entitlement_id"],
        ["id"],
    )
    op.create_index("ix_analysis_runs_offer_id", "analysis_runs", ["offer_id"], unique=False)
    op.create_index("ix_analysis_runs_entitlement_id", "analysis_runs", ["entitlement_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_entitlement_id", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_offer_id", table_name="analysis_runs")
    op.drop_constraint("fk_analysis_runs_entitlement_id", "analysis_runs", type_="foreignkey")
    op.drop_column("analysis_runs", "entitlement_id")
    op.drop_column("analysis_runs", "usage_bucket")
    op.drop_column("analysis_runs", "package_scope")
    op.drop_column("analysis_runs", "offer_id")

    op.drop_index("ix_billing_entitlements_user_offer", table_name="billing_entitlements")
    op.drop_index("ix_billing_entitlements_user_status", table_name="billing_entitlements")
    op.drop_index("ix_billing_entitlements_stripe_subscription_id", table_name="billing_entitlements")
    op.drop_index("ix_billing_entitlements_checkout_session_id", table_name="billing_entitlements")
    op.drop_index("ix_billing_entitlements_offer_id", table_name="billing_entitlements")
    op.drop_index("ix_billing_entitlements_user_id", table_name="billing_entitlements")
    op.drop_index("ix_billing_entitlements_id", table_name="billing_entitlements")
    op.drop_table("billing_entitlements")
