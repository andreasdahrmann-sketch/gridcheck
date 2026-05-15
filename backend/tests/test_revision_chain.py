"""
B.5 - Engine-Tests fuer Revisionskette (revisionssicher / GoBD).
"""
import json
from db.database import SessionLocal
from db.models import RevisionRecord
from engine.revision import (
    speichere_revision,
    lade_revisionen,
    pruefe_integritaet,
    SCHEMA_VERSION,
)


def _dummy_daten(seed: int = 1):
    return {
        "eingabe": {"leistung_mw": float(seed), "anlagentyp": "PV"},
        "scores": {"gesamt": seed * 10},
        "fazit": {"bewertung": "GRUEN"},
    }


class TestGenesis:
    def test_leere_chain_ist_integer(self, isolierte_revisionen):
        res = pruefe_integritaet()
        assert res["ok"] is True
        assert res["anzahl"] == 0
        assert res["fehler"] == []


class TestAppendOnly:
    def test_revisionsnummer_inkrementiert(self, isolierte_revisionen):
        r1 = speichere_revision(_dummy_daten(1), engine_version="test-1.0.0")
        r2 = speichere_revision(_dummy_daten(2), engine_version="test-1.0.0")
        r3 = speichere_revision(_dummy_daten(3), engine_version="test-1.0.0")
        assert r1["revisionsnummer"] == 1
        assert r2["revisionsnummer"] == 2
        assert r3["revisionsnummer"] == 3

    def test_jeder_eintrag_hat_pflichtfelder(self, isolierte_revisionen):
        speichere_revision(_dummy_daten(1), engine_version="test-1.0.0")
        eintrag = lade_revisionen()[0]
        for key in ("revisionsnummer", "uuid", "timestamp", "hash",
                    "previous_hash", "schema_version", "engine_version", "daten"):
            assert key in eintrag, f"Pflichtfeld fehlt im Record: {key}"


class TestHashChain:
    def test_previous_hash_verkettet_korrekt(self, isolierte_revisionen):
        r1 = speichere_revision(_dummy_daten(1), engine_version="test-1.0.0")
        r2 = speichere_revision(_dummy_daten(2), engine_version="test-1.0.0")
        r3 = speichere_revision(_dummy_daten(3), engine_version="test-1.0.0")
        assert r2["previous_hash"] == r1["hash"]
        assert r3["previous_hash"] == r2["hash"]

    def test_pruefe_integritaet_ok_bei_3_eintraegen(self, isolierte_revisionen):
        for i in range(1, 4):
            speichere_revision(_dummy_daten(i), engine_version="test-1.0.0")
        res = pruefe_integritaet()
        assert res["ok"] is True
        assert res["anzahl"] == 3
        assert res["fehler"] == []


class TestTamperingErkennung:
    def test_manipulierte_zeile_wird_erkannt(self, isolierte_revisionen):
        speichere_revision(_dummy_daten(1), engine_version="test-1.0.0")
        speichere_revision(_dummy_daten(2), engine_version="test-1.0.0")

        db = SessionLocal()
        try:
            record = (
                db.query(RevisionRecord)
                .order_by(RevisionRecord.revisionsnummer.asc(), RevisionRecord.id.asc())
                .first()
            )
            assert record is not None
            eintrag = json.loads(record.data_json)
            eintrag["scores"]["gesamt"] = 99999  # Tampering
            record.data_json = json.dumps(eintrag, ensure_ascii=False, separators=(",", ":"))
            db.commit()
        finally:
            db.close()

        res = pruefe_integritaet()
        assert res["ok"] is False
        assert len(res["fehler"]) >= 1


class TestDryRun:
    def test_dry_run_schreibt_nicht(self, isolierte_revisionen):
        vor = len(lade_revisionen())
        r = speichere_revision(_dummy_daten(1), dry_run=True, engine_version="test-1.0.0")
        nach = len(lade_revisionen())
        assert vor == nach == 0
        assert r["revisionsnummer"] >= 1
        assert "hash" in r


class TestSchemaVersion:
    def test_schema_version_im_eintrag(self, isolierte_revisionen):
        speichere_revision(_dummy_daten(1), engine_version="test-1.0.0")
        eintrag = lade_revisionen()[0]
        assert eintrag["schema_version"] == SCHEMA_VERSION
