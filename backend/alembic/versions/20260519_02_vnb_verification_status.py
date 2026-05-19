"""vnb verification status on users

Revision ID: 20260519_02
Revises: 20260519_01
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260519_02"
down_revision = "20260519_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "vnb_verification_status",
            sa.String(length=16),
            nullable=False,
            server_default="none",
        ),
    )
    op.execute(
        """
        UPDATE users
        SET vnb_verification_status = 'pending'
        WHERE lower(role) = 'netzbetreiber'
        """
    )
    op.create_index("ix_users_vnb_verification_status", "users", ["vnb_verification_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_vnb_verification_status", table_name="users")
    op.drop_column("users", "vnb_verification_status")
