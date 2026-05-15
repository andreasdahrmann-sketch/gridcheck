from __future__ import annotations

from services.data_source_pipeline import run_data_source_pipeline


def test_pipeline_not_configured_sources_have_required_fields(monkeypatch):
    monkeypatch.delenv("MASTR_EXPORT_URL", raising=False)
    monkeypatch.delenv("DWD_SOURCE_URL", raising=False)

    snaps = run_data_source_pipeline(["mastr", "dwd"])
    assert len(snaps) == 2
    for s in snaps:
        assert s.name in {"MaStR", "DWD"}
        assert s.raw_hash
        assert s.normalized_hash
        assert s.parser_version
        assert s.validierungsstatus in {"NOT_CONFIGURED", "OK", "PARTIAL", "ERROR"}
        assert s.datenklasse in {"A", "B", "C", "D", "E"}

