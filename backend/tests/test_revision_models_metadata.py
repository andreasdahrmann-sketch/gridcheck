from __future__ import annotations

from db.models import Base, KiFeedbackRecord, ReportRevisionRecord, RevisionRecord


def test_revision_chain_models_are_registered_in_metadata() -> None:
    tables = Base.metadata.tables

    assert RevisionRecord.__tablename__ in tables
    assert KiFeedbackRecord.__tablename__ in tables
    assert ReportRevisionRecord.__tablename__ in tables


def test_revision_chain_models_expose_expected_columns() -> None:
    revision_columns = set(RevisionRecord.__table__.columns.keys())
    feedback_columns = set(KiFeedbackRecord.__table__.columns.keys())
    report_columns = set(ReportRevisionRecord.__table__.columns.keys())

    assert {
        "revisionsnummer",
        "uuid",
        "timestamp",
        "schema_version",
        "engine_version",
        "previous_hash",
        "hash",
        "actor_user_id",
        "action_type",
        "project_id",
        "data_json",
    } <= revision_columns
    assert {
        "feedback_nummer",
        "uuid",
        "timestamp",
        "schema_version",
        "previous_hash",
        "hash",
        "actor_user_id",
        "revision_hash",
        "data_json",
    } <= feedback_columns
    assert {
        "revisionsnummer",
        "uuid",
        "timestamp",
        "schema_version",
        "report_type",
        "previous_hash",
        "hash",
        "engine_revision_hash",
        "report_json",
        "html_content",
    } <= report_columns
