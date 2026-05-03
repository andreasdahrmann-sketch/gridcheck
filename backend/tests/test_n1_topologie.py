from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.berechnung import berechne_netzanschluss


def assert_equal(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: erwartet {expected!r}, erhalten {actual!r}")


def test_ms_pv_5mw_topologie_unbekannt():
    eingabe = {
        "anlagentyp": "PV",
        "p_kw": 5000,
        "leistung_mw": 5.0,
        "plz": "00000",
        "nennspannung": 20,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 10,
        "anschlussart": "Einspeisung",
        "cos_phi": 0.95,
        "parallele_systeme": 2,
        "redundanz": True,
        "bestehende_einspeisung_mw": 0
    }

    result = berechne_netzanschluss(eingabe)
    n1 = result.get("n1", {})
    fazit = result.get("fazit", {})

    assert_equal("status", result.get("status"), "OK")
    assert_equal("topologie", n1.get("topologie"), "unbekannt")
    assert_equal("topologie_n1", n1.get("topologie_n1"), False)
    assert_equal("n1_sicher", n1.get("n1_sicher"), False)
    assert_equal("bewertung", n1.get("bewertung"), "ROT")
    assert_equal("entscheidung", fazit.get("entscheidung"), "C")


if __name__ == "__main__":
    test_ms_pv_5mw_topologie_unbekannt()
    print("OK: tests/test_n1_topologie.py erfolgreich")
