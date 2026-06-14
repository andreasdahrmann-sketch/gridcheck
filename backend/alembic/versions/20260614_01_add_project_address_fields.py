"""add project address fields (street, house_number, city, lat, lon) and relax plz NOT NULL

Revision ID: 20260614_01
Revises: 20260519_03
Create Date: 2026-06-14

Begruendung:
- User-Anforderung: Standort entweder per Adresse (Strasse + Hausnr + PLZ + Ort)
  ODER per Koordinaten (lat/lon) — beides gleichberechtigt.
- Latitude/Longitude werden als reine WGS84-Dezimalgrade gespeichert.
- PLZ wird nullable, weil reine lat/lon-Eingabe ohne Adresse moeglich sein muss.
- Reversibel: down() entfernt die neuen Spalten und stellt NOT-NULL auf plz wieder her.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260614_01"
down_revision = "20260519_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("street", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("house_number", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("city", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("longitude", sa.Float(), nullable=True))
    op.alter_column("projects", "plz", existing_type=sa.String(length=5), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE projects SET plz = '' WHERE plz IS NULL")
    op.alter_column("projects", "plz", existing_type=sa.String(length=5), nullable=False)
    op.drop_column("projects", "longitude")
    op.drop_column("projects", "latitude")
    op.drop_column("projects", "city")
    op.drop_column("projects", "house_number")
    op.drop_column("projects", "street")
