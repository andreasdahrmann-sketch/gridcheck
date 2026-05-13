"""add postgres-backed revision and report chains

Revision ID: 20260512_03
Revises: 20260512_02
Create Date: 2026-05-12 20:55:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260512_03"
down_revision = "20260512_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revision_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("revisionsnummer", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("engine_version", sa.String(), nullable=False),
        sa.Column("previous_hash", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revisionsnummer", name="uq_revision_records_number"),
        sa.UniqueConstraint("uuid", name="uq_revision_records_uuid"),
        sa.UniqueConstraint("hash", name="uq_revision_records_hash"),
    )
    op.create_index("ix_revision_records_id", "revision_records", ["id"], unique=False)
    op.create_index("ix_revision_records_revisionsnummer", "revision_records", ["revisionsnummer"], unique=False)
    op.create_index("ix_revision_records_hash", "revision_records", ["hash"], unique=False)
    op.create_index("ix_revision_records_actor_user_id", "revision_records", ["actor_user_id"], unique=False)
    op.create_index("ix_revision_records_project_id", "revision_records", ["project_id"], unique=False)
    op.create_index(
        "ix_revision_records_project_number",
        "revision_records",
        ["project_id", "revisionsnummer"],
        unique=False,
    )
    op.create_index(
        "ix_revision_records_action_timestamp",
        "revision_records",
        ["action_type", "timestamp"],
        unique=False,
    )

    op.create_table(
        "ki_feedback_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feedback_nummer", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("previous_hash", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("revision_hash", sa.String(), nullable=True),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feedback_nummer", name="uq_ki_feedback_records_number"),
        sa.UniqueConstraint("uuid", name="uq_ki_feedback_records_uuid"),
        sa.UniqueConstraint("hash", name="uq_ki_feedback_records_hash"),
    )
    op.create_index("ix_ki_feedback_records_id", "ki_feedback_records", ["id"], unique=False)
    op.create_index("ix_ki_feedback_records_feedback_nummer", "ki_feedback_records", ["feedback_nummer"], unique=False)
    op.create_index("ix_ki_feedback_records_hash", "ki_feedback_records", ["hash"], unique=False)
    op.create_index("ix_ki_feedback_records_actor_user_id", "ki_feedback_records", ["actor_user_id"], unique=False)
    op.create_index("ix_ki_feedback_records_revision_hash", "ki_feedback_records", ["revision_hash"], unique=False)
    op.create_index(
        "ix_ki_feedback_records_revision_number",
        "ki_feedback_records",
        ["revision_hash", "feedback_nummer"],
        unique=False,
    )

    op.create_table(
        "report_revision_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("revisionsnummer", sa.BigInteger(), nullable=False),
        sa.Column("uuid", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("previous_hash", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("engine_revision_hash", sa.String(), nullable=True),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revisionsnummer", name="uq_report_revision_records_number"),
        sa.UniqueConstraint("uuid", name="uq_report_revision_records_uuid"),
        sa.UniqueConstraint("hash", name="uq_report_revision_records_hash"),
    )
    op.create_index("ix_report_revision_records_id", "report_revision_records", ["id"], unique=False)
    op.create_index(
        "ix_report_revision_records_revisionsnummer",
        "report_revision_records",
        ["revisionsnummer"],
        unique=False,
    )
    op.create_index("ix_report_revision_records_hash", "report_revision_records", ["hash"], unique=False)
    op.create_index(
        "ix_report_revision_records_engine_revision_hash",
        "report_revision_records",
        ["engine_revision_hash"],
        unique=False,
    )
    op.create_index(
        "ix_report_revision_records_type_number",
        "report_revision_records",
        ["report_type", "revisionsnummer"],
        unique=False,
    )
    op.create_index(
        "ix_report_revision_records_engine_hash",
        "report_revision_records",
        ["engine_revision_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_report_revision_records_engine_hash", table_name="report_revision_records")
    op.drop_index("ix_report_revision_records_type_number", table_name="report_revision_records")
    op.drop_index("ix_report_revision_records_engine_revision_hash", table_name="report_revision_records")
    op.drop_index("ix_report_revision_records_hash", table_name="report_revision_records")
    op.drop_index("ix_report_revision_records_revisionsnummer", table_name="report_revision_records")
    op.drop_index("ix_report_revision_records_id", table_name="report_revision_records")
    op.drop_table("report_revision_records")

    op.drop_index("ix_ki_feedback_records_revision_number", table_name="ki_feedback_records")
    op.drop_index("ix_ki_feedback_records_revision_hash", table_name="ki_feedback_records")
    op.drop_index("ix_ki_feedback_records_actor_user_id", table_name="ki_feedback_records")
    op.drop_index("ix_ki_feedback_records_hash", table_name="ki_feedback_records")
    op.drop_index("ix_ki_feedback_records_feedback_nummer", table_name="ki_feedback_records")
    op.drop_index("ix_ki_feedback_records_id", table_name="ki_feedback_records")
    op.drop_table("ki_feedback_records")

    op.drop_index("ix_revision_records_action_timestamp", table_name="revision_records")
    op.drop_index("ix_revision_records_project_number", table_name="revision_records")
    op.drop_index("ix_revision_records_project_id", table_name="revision_records")
    op.drop_index("ix_revision_records_actor_user_id", table_name="revision_records")
    op.drop_index("ix_revision_records_hash", table_name="revision_records")
    op.drop_index("ix_revision_records_revisionsnummer", table_name="revision_records")
    op.drop_index("ix_revision_records_id", table_name="revision_records")
    op.drop_table("revision_records")
