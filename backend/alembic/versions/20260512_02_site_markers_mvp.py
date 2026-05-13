"""add site marker mvp table

Revision ID: 20260512_02
Revises: 20260512_01
Create Date: 2026-05-12 14:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260512_02"
down_revision = "20260512_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_markers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("location_source", sa.String(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("verification_status", sa.String(), nullable=False, server_default="unverified"),
        sa.Column("photo_file_name", sa.String(), nullable=False),
        sa.Column("photo_mime_type", sa.String(), nullable=False),
        sa.Column("photo_size_bytes", sa.Integer(), nullable=False),
        sa.Column("photo_storage_path", sa.Text(), nullable=False),
        sa.Column("photo_checksum", sa.String(), nullable=False),
        sa.Column("revision_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_markers_id", "site_markers", ["id"], unique=False)
    op.create_index("ix_site_markers_created_by_user_id", "site_markers", ["created_by_user_id"], unique=False)
    op.create_index("ix_site_markers_revision_hash", "site_markers", ["revision_hash"], unique=False)
    op.create_index(
        "ix_site_markers_created_by_created",
        "site_markers",
        ["created_by_user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_site_markers_created_by_created", table_name="site_markers")
    op.drop_index("ix_site_markers_revision_hash", table_name="site_markers")
    op.drop_index("ix_site_markers_created_by_user_id", table_name="site_markers")
    op.drop_index("ix_site_markers_id", table_name="site_markers")
    op.drop_table("site_markers")
