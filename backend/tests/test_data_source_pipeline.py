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
        _assert_confidence_fields(s)


def _assert_confidence_fields(snap) -> None:
    for field in (
        "confidence_score",
        "confidence_technisch",
        "confidence_geometrisch",
        "confidence_kommerziell",
    ):
        value = getattr(snap, field)
        assert isinstance(value, int)
        assert 0 <= value <= 100


def test_smard_snapshot_has_confidence_and_no_capacity_claim(monkeypatch):
    snaps = run_data_source_pipeline(["smard"])
    assert len(snaps) == 1
    smard = snaps[0]
    assert smard.name == "SMARD"
    _assert_confidence_fields(smard)
    assert smard.validierungsstatus in {"OK", "PARTIAL", "ERROR"}
    normalized_repr = str(smard.normalized_hash).lower()
    assert "freie_kapazitaet" not in normalized_repr
    assert "free_capacity" not in normalized_repr

