"""add data source pipeline model tables

Revision ID: 20260510_01
Revises: b6b9e5a3cbd3
Create Date: 2026-05-10 17:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260510_01"
down_revision = "b6b9e5a3cbd3"
branch_labels = None
depends_on = None


def _source_columns() -> list[sa.Column]:
    return [
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_license", sa.String(), nullable=True),
        sa.Column("source_imported_at", sa.DateTime(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        sa.Column("source_raw_hash", sa.String(), nullable=False),
        sa.Column("source_normalized_hash", sa.String(), nullable=False),
        sa.Column("source_parser_version", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_technical", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_geometric", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_commercial", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_status", sa.String(), nullable=False, server_default="UNKNOWN"),
        sa.Column("data_class", sa.String(), nullable=False, server_default="C"),
    ]


def upgrade() -> None:
    op.create_table(
        "asset_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        *_source_columns(),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("geometry_wkt", sa.Text(), nullable=True),
        sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_candidates_id", "asset_candidates", ["id"], unique=False)

    op.create_table(
        "generation_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        *_source_columns(),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("energy_carrier", sa.String(), nullable=False),
        sa.Column("capacity_kw", sa.Float(), nullable=True),
        sa.Column("plz", sa.String(length=5), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generation_assets_id", "generation_assets", ["id"], unique=False)

    op.create_table(
        "system_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        *_source_columns(),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("signal_value", sa.Float(), nullable=True),
        sa.Column("signal_unit", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("measured_at", sa.DateTime(), nullable=True),
        sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_signals_id", "system_signals", ["id"], unique=False)

    op.create_table(
        "weather_resource",
        sa.Column("id", sa.Integer(), nullable=False),
        *_source_columns(),
        sa.Column("station_id", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("measured_at", sa.DateTime(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("wind_ms", sa.Float(), nullable=True),
        sa.Column("irradiation_wm2", sa.Float(), nullable=True),
        sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weather_resource_id", "weather_resource", ["id"], unique=False)

    op.create_table(
        "ground_risk",
        sa.Column("id", sa.Integer(), nullable=False),
        *_source_columns(),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("soil_class", sa.String(), nullable=True),
        sa.Column("groundwater_level_m", sa.Float(), nullable=True),
        sa.Column("excavation_risk_score", sa.Float(), nullable=True),
        sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ground_risk_id", "ground_risk", ["id"], unique=False)

    op.create_table(
        "cost_indices",
        sa.Column("id", sa.Integer(), nullable=False),
        *_source_columns(),
        sa.Column("index_type", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("index_value", sa.Float(), nullable=True),
        sa.Column("index_unit", sa.String(), nullable=True),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cost_indices_id", "cost_indices", ["id"], unique=False)

    op.create_table(
        "gridcheck_result_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("scoring_version", sa.String(), nullable=False),
        sa.Column("norm_version", sa.String(), nullable=False),
        sa.Column("app_version", sa.String(), nullable=False),
        sa.Column("inputs_json", sa.Text(), nullable=False),
        sa.Column("assumptions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("score_components_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sources_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("result_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gridcheck_result_audit_id", "gridcheck_result_audit", ["id"], unique=False)
    op.create_index(
        "ix_gridcheck_result_audit_project_id",
        "gridcheck_result_audit",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_gridcheck_result_audit_project_id", table_name="gridcheck_result_audit")
    op.drop_index("ix_gridcheck_result_audit_id", table_name="gridcheck_result_audit")
    op.drop_table("gridcheck_result_audit")
    op.drop_index("ix_cost_indices_id", table_name="cost_indices")
    op.drop_table("cost_indices")
    op.drop_index("ix_ground_risk_id", table_name="ground_risk")
    op.drop_table("ground_risk")
    op.drop_index("ix_weather_resource_id", table_name="weather_resource")
    op.drop_table("weather_resource")
    op.drop_index("ix_system_signals_id", table_name="system_signals")
    op.drop_table("system_signals")
    op.drop_index("ix_generation_assets_id", table_name="generation_assets")
    op.drop_table("generation_assets")
    op.drop_index("ix_asset_candidates_id", table_name="asset_candidates")
    op.drop_table("asset_candidates")

