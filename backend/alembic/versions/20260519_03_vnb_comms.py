"""vnb operator communication threads and messages

Revision ID: 20260519_03
Revises: 20260519_02
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260519_03"
down_revision = "20260519_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vnb_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_scope", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("target_vnb_region", sa.String(length=80), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vnb_threads_id", "vnb_threads", ["id"], unique=False)
    op.create_index("ix_vnb_threads_created_by_user_id", "vnb_threads", ["created_by_user_id"], unique=False)
    op.create_index("ix_vnb_threads_board_last_message", "vnb_threads", ["board_scope", "last_message_at"], unique=False)
    op.create_index("ix_vnb_threads_category", "vnb_threads", ["category"], unique=False)

    op.create_table(
        "vnb_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["thread_id"], ["vnb_threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vnb_messages_id", "vnb_messages", ["id"], unique=False)
    op.create_index("ix_vnb_messages_thread_id", "vnb_messages", ["thread_id"], unique=False)
    op.create_index("ix_vnb_messages_sender_user_id", "vnb_messages", ["sender_user_id"], unique=False)
    op.create_index("ix_vnb_messages_thread_created", "vnb_messages", ["thread_id", "created_at"], unique=False)

    op.create_table(
        "vnb_message_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["vnb_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vnb_message_audit_id", "vnb_message_audit", ["id"], unique=False)
    op.create_index("ix_vnb_message_audit_message_id", "vnb_message_audit", ["message_id"], unique=False)
    op.create_index("ix_vnb_message_audit_actor_user_id", "vnb_message_audit", ["actor_user_id"], unique=False)
    op.create_index(
        "ix_vnb_message_audit_message_created",
        "vnb_message_audit",
        ["message_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_vnb_message_audit_message_created", table_name="vnb_message_audit")
    op.drop_index("ix_vnb_message_audit_actor_user_id", table_name="vnb_message_audit")
    op.drop_index("ix_vnb_message_audit_message_id", table_name="vnb_message_audit")
    op.drop_index("ix_vnb_message_audit_id", table_name="vnb_message_audit")
    op.drop_table("vnb_message_audit")

    op.drop_index("ix_vnb_messages_thread_created", table_name="vnb_messages")
    op.drop_index("ix_vnb_messages_sender_user_id", table_name="vnb_messages")
    op.drop_index("ix_vnb_messages_thread_id", table_name="vnb_messages")
    op.drop_index("ix_vnb_messages_id", table_name="vnb_messages")
    op.drop_table("vnb_messages")

    op.drop_index("ix_vnb_threads_category", table_name="vnb_threads")
    op.drop_index("ix_vnb_threads_board_last_message", table_name="vnb_threads")
    op.drop_index("ix_vnb_threads_created_by_user_id", table_name="vnb_threads")
    op.drop_index("ix_vnb_threads_id", table_name="vnb_threads")
    op.drop_table("vnb_threads")
