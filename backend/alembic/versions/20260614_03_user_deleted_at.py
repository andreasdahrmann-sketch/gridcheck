"""add users.deleted_at + deleted_email_hash for DSGVO Art. 17 soft-delete

Revision ID: 20260614_03
Revises: 20260614_02
Create Date: 2026-06-14

Begruendung:
- DSGVO Art. 17 (Recht auf Loeschung) wird ueber Soft-Delete realisiert.
- Hard-Delete verletzt Revisionssicherheit (Rule 05), Audit-Hash-Kette und
  Aufbewahrungspflichten (HGB/AO 6-10 Jahre fuer abrechnungsrelevante Daten).
- `deleted_at` markiert anonymisierten Nutzer-Datensatz; Login-Pfad lehnt ihn ab.
- `deleted_email_hash` (SHA256 der originalen E-Mail) sperrt Re-Registrierung
  derselben Adresse nach Anonymisierung.
- Reversibel: down() entfernt Spalten + Indizes.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260614_03"
down_revision = "20260614_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("deleted_email_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"], unique=False)
    op.create_index("ix_users_deleted_email_hash", "users", ["deleted_email_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_deleted_email_hash", table_name="users")
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_column("users", "deleted_email_hash")
    op.drop_column("users", "deleted_at")
