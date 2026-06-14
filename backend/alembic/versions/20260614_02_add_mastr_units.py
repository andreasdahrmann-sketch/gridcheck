"""add mastr_units + mastr_imports tables (BL-GIS-003 Skeleton)

Revision ID: 20260614_02
Revises: 20260614_01
Create Date: 2026-06-14

Erstes Inkrement der GIS-Pipeline (Marktstammdatenregister Skeleton).
- KEIN Live-Import, nur Persistenzschicht + Audit-Tabelle pro Importlauf.
- Datenklasse A laut Cursor-Rule 06 (offizielle BNetzA-Quelle).
- Felder für Provenienz: raw_hash, normalized_hash, parser_version,
  imported_at, source_updated_at.
- Indizes für Standortsuche (PLZ/Bundesland/lat/lon) — PostGIS-Geom kommt
  im naechsten Inkrement (BL-GIS-004).

Reversibel: down() entfernt beide Tabellen sauber.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260614_02"
down_revision = "20260614_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mastr_units",
        sa.Column("mastr_id", sa.String(length=64), nullable=False),
        sa.Column("unit_type", sa.String(length=20), nullable=False),
        sa.Column("installed_capacity_kw", sa.Numeric(14, 3), nullable=False),
        sa.Column("commissioning_date", sa.Date(), nullable=True),
        sa.Column("decommissioning_date", sa.Date(), nullable=True),
        sa.Column("plz", sa.String(length=10), nullable=True),
        sa.Column("bundesland", sa.String(length=50), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("dso_name", sa.String(length=200), nullable=True),
        sa.Column("voltage_level", sa.String(length=50), nullable=True),
        sa.Column("data_source", sa.String(length=20), nullable=False, server_default="mastr"),
        sa.Column("data_class", sa.String(length=1), nullable=False, server_default="A"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0.950"),
        sa.Column("raw_hash", sa.String(length=64), nullable=False),
        sa.Column("normalized_hash", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=20), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("mastr_id"),
    )
    op.create_index("ix_mastr_units_plz", "mastr_units", ["plz"], unique=False)
    op.create_index("ix_mastr_units_bundesland", "mastr_units", ["bundesland"], unique=False)
    op.create_index("ix_mastr_units_latitude", "mastr_units", ["latitude"], unique=False)
    op.create_index("ix_mastr_units_longitude", "mastr_units", ["longitude"], unique=False)
    op.create_index("ix_mastr_units_unit_type", "mastr_units", ["unit_type"], unique=False)

    op.create_table(
        "mastr_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("parser_version", sa.String(length=20), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("rows_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mastr_imports_started_at", "mastr_imports", ["started_at"], unique=False)
    op.create_index("ix_mastr_imports_status", "mastr_imports", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mastr_imports_status", table_name="mastr_imports")
    op.drop_index("ix_mastr_imports_started_at", table_name="mastr_imports")
    op.drop_table("mastr_imports")
    op.drop_index("ix_mastr_units_unit_type", table_name="mastr_units")
    op.drop_index("ix_mastr_units_longitude", table_name="mastr_units")
    op.drop_index("ix_mastr_units_latitude", table_name="mastr_units")
    op.drop_index("ix_mastr_units_bundesland", table_name="mastr_units")
    op.drop_index("ix_mastr_units_plz", table_name="mastr_units")
    op.drop_table("mastr_units")
