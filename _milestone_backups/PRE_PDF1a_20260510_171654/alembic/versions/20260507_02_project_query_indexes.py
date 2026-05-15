"""add project query indexes

Revision ID: 20260507_02
Revises: 20260507_01
Create Date: 2026-05-07 22:10:00
"""

from __future__ import annotations

from alembic import op


revision = "20260507_02"
down_revision = "20260507_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"], unique=False)
    op.create_index(
        "ix_projects_owner_deleted_updated",
        "projects",
        ["owner_user_id", "deleted_at", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_projects_owner_deleted_updated", table_name="projects")
    op.drop_index("ix_projects_deleted_at", table_name="projects")
