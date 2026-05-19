"""
engine/n1_analyse.py - Orchestrator fuer planerisch belastbarere N-1-Analyse (MS).

Bewertet 5 Komponenten und trennt bewusst zwischen Topologie-Heuristik,
Betriebsmittel-/Abgangsreserve und weiterem Screening:
  1. Topologie          (Adapter zu n1_ms.bewerte_n1_ms)
  2. Leitung-N-1        (Auslastung bei Ausfall eines Parallelsystems)
  3. Abgangsreserve     (konservative Umschalt-/Abgangsreserve fuer den Zubau)
  4. Trafo-N-1          (Auslastung bei Ausfall eines UW-Trafos)
  5. Spannung-N-1       (delta U bei Ausfall eines Parallelsystems)

Die N1-Klasse N1-0..N1-4 beschreibt bewusst die Nachweistiefe und nicht die
Qualitaet des Ergebnisses. Ohne verifizierte Netzbetreiberdaten bleibt die
externe Aussage im MVP maximal bei N1-2 (siehe 06-arbeitsweise-gridcheck.mdc).
"""
from __future__ import annotations

import math
from typing import Any

from constants import MS_SPANNUNG_N1_SCREENING
from engine.n1_ms import bewerte_n1_ms

VERSION = "n1-analyse-1.1.0"
BACKEND = "heuristik_v2_planer"

# ----------------------------------------------------------------------
# GRENZWERTE (fachlich validiert, siehe Modul-Docstring)
# ----------------------------------------------------------------------
GRENZEN = {
    "trafo": {
        "gruen_max_prozent": 100.0,
        "gelb_max_prozent": 120.0,
    },
    "leitung": {
        "gruen_max_prozent": 100.0,
        "gelb_max_prozent": 135.0,
    },
    "spannung_n1": {
        "gruen_max_prozent": 5.0,
        "gelb_max_prozent": 10.0,
    },
    "abgang_reserve_ratio": {
        "gruen_min": 1.00,
        "gelb_min": 0.80,
    },
}

DATENQUELLEN_ALIAS = {
    "unknown": "unknown",
    "planner_assumption": "planner_assumption",
    "planer": "planner_assumption",
    "engineering_estimate": "planner_assumption",
    "user_estimate": "user_estimate",
    "user": "user_estimate",
    "manual": "user_estimate",
    "dso_verified": "dso_verified",
    "netzbetreiber": "dso_verified",
    "vnb": "dso_verified",
}


# ----------------------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------------------
def _f(x, default=None):
    """None-/Fehler-sicheres float-Casting."""
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def _bool(x, default: bool = False) -> bool:
    if isinstance(x, bool):
        return x
    if x is None:
        return default
    if isinstance(x, str):
        lowered = x.strip().lower()
        if lowered in {"1", "true", "yes", "ja", "on"}:
            return True
        if lowered in {"0", "false", "no", "nein", "off"}:
            return False
    return bool(x)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _bewertung_aus_prozent(p: float, gruen_max: float, gelb_max: float) -> str:
    """Klassifiziert Auslastung in GRUEN/GELB/ROT."""
    if p <= gruen_max:
        return "GRUEN"
    if p <= gelb_max:
        return "GELB"
    return "ROT"


def _max_bewertung(*bewertungen: str) -> str:
    """Schlechteste Bewertung gewinnt (worst-case)."""
    rang = {"GRUEN": 0, "GELB": 1, "ROT": 2, "NICHT_GEPRUEFT": -1}
    aktiv = [b for b in bewertungen if b in rang and rang[b] >= 0]
    if not aktiv:
        return "NICHT_GEPRUEFT"
    return max(aktiv, key=lambda b: rang[b])


def _ist_geprueft(component: dict | None) -> bool:
    if not isinstance(component, dict):
        return False
    return component.get("bewertung") not in (None, "NICHT_GEPRUEFT")


def _datenquelle(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    return DATENQUELLEN_ALIAS.get(normalized, "unknown")


def _extrahiere_abgaenge(eingabe: dict[str, Any]) -> list[dict[str, Any]]:
    umspannwerk = eingabe.get("umspannwerk")
    if isinstance(umspannwerk, dict):
        raw = umspannwerk.get("abgaenge")
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
    raw = eingabe.get("abgaenge")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _ist_dso_verifiziert(eingabe: dict[str, Any]) -> bool:
    if _bool(eingabe.get("dso_verified")) or _bool(eingabe.get("n1_dso_verified")):
        return True
    quellen = [eingabe.get("n1_datengrundlage")]
    umspannwerk = eingabe.get("umspannwerk")
    if isinstance(umspannwerk, dict):
        quellen.append(umspannwerk.get("datenquelle"))
    for abgang in _extrahiere_abgaenge(eingabe):
        quellen.append(abgang.get("datenquelle"))
    return any(_datenquelle(quelle) == "dso_verified" for quelle in quellen)


def _zusatzstrom_a(zusatzlast_mw: float, cos_phi: float, nennspannung_kv: float | None) -> float | None:
    u_kv = _f(nennspannung_kv)
    if u_kv is None or u_kv <= 0:
        return None
    cphi = _f(cos_phi, 0.95) or 0.95
    if cphi <= 0:
        cphi = 0.95
    s_mva = abs(_f(zusatzlast_mw, 0.0) or 0.0) / cphi
    if s_mva <= 0:
        return 0.0
    return (s_mva * 1e6) / (math.sqrt(3) * u_kv * 1000.0)


def _reserve_a(abgang: dict[str, Any]) -> float | None:
    reserve_explicit = _f(abgang.get("reserve_n1_a"))
    if reserve_explicit is not None:
        return max(0.0, reserve_explicit)
    reserve_generic = _f(abgang.get("reserve_i_a"))
    if reserve_generic is not None:
        return max(0.0, reserve_generic)
    i_max = _f(abgang.get("i_max_a"))
    last = _f(abgang.get("belastung_aktuell_a"))
    if i_max is None or last is None:
        return None
    return max(0.0, i_max - last)


def _stufenbegruendung(n1_klasse: str, *, dso_daten_vorhanden: bool) -> str:
    mapping = {
        "N1-0": "Kein belastbares N-1-Screening moeglich.",
        "N1-1": "Nur Topologie/Umschaltkonzept heuristisch bewertet; Betriebsmittelreserve noch nicht belastbar nachgewiesen.",
        "N1-2": "Topologie plus Leitungs- oder Abgangsreserve gescreent; Trafo- und/oder Spannungsnachweis noch unvollstaendig.",
        "N1-3": "Topologie, Pfad/Betriebsmittel, Trafo und Spannung gescreent; weiterhin ohne verifizierte Netzbetreiberdaten.",
        "N1-4": "Topologie, Betriebsmittel, Trafo und Spannung mit verifizierten Netzbetreiberdaten abgesichert.",
    }
    if n1_klasse == "N1-3" and dso_daten_vorhanden:
        return "Topologie, Betriebsmittel, Trafo und Spannung sind bewertet; die Datengrundlage wirkt verifiziert, bleibt aber im Screening konservativ."
    return mapping.get(n1_klasse, "N-1-Stufe nicht eindeutig klassifizierbar.")


def _nachweise(
    n1_topo: dict[str, Any],
    n1_leit: dict[str, Any],
    n1_abgang: dict[str, Any],
    n1_trafo: dict[str, Any],
    n1_spg: dict[str, Any],
    *,
    dso_daten_vorhanden: bool,
) -> tuple[list[str], list[str]]:
    vorhanden: list[str] = []
    fehlend: list[str] = []

    if _ist_geprueft(n1_topo):
        vorhanden.append("Topologie / Umschaltkonzept")
    else:
        fehlend.append("Topologie / Umschaltkonzept")

    if _ist_geprueft(n1_abgang):
        vorhanden.append("Abgangsreserve / Betriebsmittelpfad")
    elif _ist_geprueft(n1_leit):
        vorhanden.append("Leitungsreserve im N-1-Fall")
        fehlend.append("Explizite Abgangsreserve / Umschaltreserve")
    else:
        fehlend.append("Leitungs- oder Abgangsreserve im N-1-Fall")

    if _ist_geprueft(n1_trafo):
        vorhanden.append("Umspannwerks-Traforeserve")
    else:
        fehlend.append("Umspannwerks-Traforeserve")

    if _ist_geprueft(n1_spg):
        vorhanden.append("Spannungshaltung im N-1-Fall")
    else:
        fehlend.append("Spannungshaltung im N-1-Fall")

    if dso_daten_vorhanden:
        vorhanden.append("Verifizierte Netzbetreiberdaten")
    else:
        fehlend.append("Verifizierte Netzbetreiberdaten")

    return vorhanden, fehlend


# ----------------------------------------------------------------------
# 1. Trafo-N-1
# ----------------------------------------------------------------------
def bewerte_trafo_n1(umspannwerk: dict | None, zusatzlast_mw: float, cos_phi: float) -> dict:
    """
    Trafo-N-1: Bei Ausfall des groessten Trafos muessen die restlichen die Gesamtlast tragen.
    """
    if not umspannwerk or not umspannwerk.get("trafos"):
        return {
            "bewertung": "NICHT_GEPRUEFT",
            "auslastung_n1_prozent": None,
            "engpass_trafo_idx": -1,
            "begruendung_technisch": "Keine Trafodaten vorhanden - Trafo-N-1 nicht geprueft.",
            "begruendung_klartext": "Es liegen keine Daten zum Umspannwerk vor. Trafoausfall wurde nicht geprueft.",
        }

    trafos = [item for item in _as_list(umspannwerk.get("trafos")) if isinstance(item, dict)]
    if len(trafos) < 2:
        return {
            "bewertung": "ROT",
            "auslastung_n1_prozent": None,
            "engpass_trafo_idx": 0,
            "begruendung_technisch": f"UW hat nur {len(trafos)} Trafo - keine N-1-Redundanz moeglich.",
            "begruendung_klartext": "Im Umspannwerk steht nur ein einziger Transformator zur Verfuegung. Bei dessen Ausfall gibt es keine Reserve.",
        }

    cphi = _f(cos_phi, 0.95) or 0.95
    if cphi <= 0:
        cphi = 0.95
    zusatz_mva = abs(_f(zusatzlast_mw, 0.0) or 0.0) / cphi

    last_aktuell_mva = 0.0
    sn_total_mva = 0.0
    for trafo in trafos:
        last_aktuell_mva += abs(_f(trafo.get("belastung_aktuell_mw"), 0.0) or 0.0) / cphi
        sn_total_mva += _f(trafo.get("sn_mva"), 0.0) or 0.0

    last_gesamt_mva = last_aktuell_mva + zusatz_mva

    sn_max = max((_f(trafo.get("sn_mva"), 0.0) or 0.0) for trafo in trafos)
    idx_max = max(range(len(trafos)), key=lambda idx: _f(trafos[idx].get("sn_mva"), 0.0) or 0.0)
    sn_rest = sn_total_mva - sn_max

    if sn_rest <= 0:
        return {
            "bewertung": "ROT",
            "auslastung_n1_prozent": None,
            "engpass_trafo_idx": idx_max,
            "begruendung_technisch": "Restkapazitaet nach Trafo-N-1 = 0 MVA.",
            "begruendung_klartext": "Wenn der groesste Transformator ausfaellt, bleibt keine Trafokapazitaet uebrig.",
        }

    auslastung_n1 = (last_gesamt_mva / sn_rest) * 100.0
    bewertung = _bewertung_aus_prozent(
        auslastung_n1,
        GRENZEN["trafo"]["gruen_max_prozent"],
        GRENZEN["trafo"]["gelb_max_prozent"],
    )

    begruendung_technisch = (
        f"N-1 Trafo: Last_ges={last_gesamt_mva:.2f} MVA (inkl. Zusatz {zusatz_mva:.2f} MVA), "
        f"Sn_rest={sn_rest:.2f} MVA nach Ausfall T{idx_max} ({sn_max:.1f} MVA) -> "
        f"Auslastung_N1={auslastung_n1:.1f}% (Grenzen: GRUEN<={GRENZEN['trafo']['gruen_max_prozent']}%, "
        f"GELB<={GRENZEN['trafo']['gelb_max_prozent']}%)."
    )

    if bewertung == "GRUEN":
        begruendung_klartext = (
            f"Auch bei Ausfall des groessten Trafos im Umspannwerk reicht die verbleibende Kapazitaet "
            f"({auslastung_n1:.0f}% Auslastung). Reserve vorhanden."
        )
    elif bewertung == "GELB":
        begruendung_klartext = (
            f"Bei Ausfall des groessten Trafos liegt die Auslastung bei {auslastung_n1:.0f}%. "
            "Kurzzeitueberlast mag moeglich sein, bleibt aber planerisch ein Engpassrisiko."
        )
    else:
        begruendung_klartext = (
            f"Bei Ausfall des groessten Trafos waere die Auslastung {auslastung_n1:.0f}% - "
            "das ist nicht zulaessig. Trafoverstaerkung oder zusaetzlicher Trafo noetig."
        )

    return {
        "bewertung": bewertung,
        "auslastung_n1_prozent": round(auslastung_n1, 2),
        "engpass_trafo_idx": idx_max,
        "begruendung_technisch": begruendung_technisch,
        "begruendung_klartext": begruendung_klartext,
    }


# ----------------------------------------------------------------------
# 2. Leitung-N-1
# ----------------------------------------------------------------------
def bewerte_leitung_n1(thermisch_n1: dict | None) -> dict:
    """
    Leitung-N-1: Auslastung bei Ausfall eines Parallelsystems.
    """
    if not thermisch_n1:
        return {
            "bewertung": "ROT",
            "auslastung_n1_prozent": None,
            "iz_a": None,
            "i_n1_a": None,
            "begruendung_technisch": "Nur 1 Leitungssystem oder keine N-1-Berechnung moeglich.",
            "begruendung_klartext": "Bei nur einer Leitung gibt es keinen Ersatz, falls diese ausfaellt.",
        }

    auslastung = _f(thermisch_n1.get("auslastung_prozent"))
    if auslastung is None:
        return {
            "bewertung": "NICHT_GEPRUEFT",
            "auslastung_n1_prozent": None,
            "iz_a": _f(thermisch_n1.get("i_max_a")),
            "i_n1_a": _f(thermisch_n1.get("i_betrieb_a")),
            "begruendung_technisch": "Auslastung im N-1-Fall nicht ermittelbar.",
            "begruendung_klartext": "Die Auslastung der verbleibenden Leitung im Ausfallszenario konnte nicht berechnet werden.",
        }

    bewertung = _bewertung_aus_prozent(
        auslastung,
        GRENZEN["leitung"]["gruen_max_prozent"],
        GRENZEN["leitung"]["gelb_max_prozent"],
    )

    iz = _f(thermisch_n1.get("i_max_a"))
    i_n1 = _f(thermisch_n1.get("i_betrieb_a"))
    if i_n1 is None:
        i_n1 = _f(thermisch_n1.get("i_pro_system_a"))
    if i_n1 is None:
        i_n1 = _f(thermisch_n1.get("i_betrieb_gesamt_a"))

    if iz and i_n1:
        begruendung_technisch = (
            f"N-1 Leitung: I_N1={i_n1:.0f} A, Iz={iz:.0f} A -> Auslastung_N1={auslastung:.1f}% "
            f"(Grenzen: GRUEN<={GRENZEN['leitung']['gruen_max_prozent']}%, "
            f"GELB<={GRENZEN['leitung']['gelb_max_prozent']}%)."
        )
    else:
        begruendung_technisch = f"N-1 Leitung: Auslastung_N1={auslastung:.1f}%."

    if bewertung == "GRUEN":
        begruendung_klartext = (
            f"Bei Ausfall eines Parallelsystems traegt das verbleibende System {auslastung:.0f}% - Dauerbetrieb plausibel."
        )
    elif bewertung == "GELB":
        begruendung_klartext = (
            f"Bei Ausfall eines Parallelsystems liegt die Auslastung bei {auslastung:.0f}%. "
            "Kurzzeitreserve mag reichen, bleibt aber grenzwertig."
        )
    else:
        begruendung_klartext = (
            f"Bei Ausfall eines Parallelsystems waere die Restleitung mit {auslastung:.0f}% ueberlastet. "
            "Staerkerer Querschnitt oder zusaetzliches System noetig."
        )

    return {
        "bewertung": bewertung,
        "auslastung_n1_prozent": round(auslastung, 2),
        "iz_a": round(iz, 1) if iz is not None else None,
        "i_n1_a": round(i_n1, 1) if i_n1 is not None else None,
        "begruendung_technisch": begruendung_technisch,
        "begruendung_klartext": begruendung_klartext,
    }


# ----------------------------------------------------------------------
# 3. Abgangsreserve / Betriebsmittel-N-1
# ----------------------------------------------------------------------
def bewerte_abgang_n1(eingabe: dict[str, Any], projektstrom_a: float | None) -> dict:
    """
    Konservatives Abgangs-/Betriebsmittel-Screening:
    Bewertet nur die beste einzelne alternative Reserve fuer den Zubau.
    Mehrfachumschaltungen oder verteilte Lastaufteilung werden ohne
    verifiziertes Umschaltkonzept bewusst NICHT unterstellt.
    """
    abgaenge = _extrahiere_abgaenge(eingabe)
    projektstrom = _f(projektstrom_a)
    if not abgaenge:
        return {
            "bewertung": "NICHT_GEPRUEFT",
            "primaer_abgang_label": None,
            "engpass_abgang_label": None,
            "abgaenge_gesamt": 0,
            "abgaenge_auswertbar": 0,
            "projektstrom_a": round(projektstrom, 1) if projektstrom is not None else None,
            "beste_reserve_a": None,
            "reserve_ratio": None,
            "begruendung_technisch": "Keine Abgangsdaten vorhanden - Umschalt-/Abgangsreserve nicht geprueft.",
            "begruendung_klartext": "Es liegen keine Angaben zu Abgaengen oder Umschaltreserven vor.",
        }

    if projektstrom is None:
        return {
            "bewertung": "NICHT_GEPRUEFT",
            "primaer_abgang_label": None,
            "engpass_abgang_label": None,
            "abgaenge_gesamt": len(abgaenge),
            "abgaenge_auswertbar": 0,
            "projektstrom_a": None,
            "beste_reserve_a": None,
            "reserve_ratio": None,
            "begruendung_technisch": "Projektstrom fuer Abgangsreserve nicht ermittelbar.",
            "begruendung_klartext": "Die fuer den Zubau relevante Stromstaerke konnte nicht bestimmt werden.",
        }

    auswertbar: list[dict[str, Any]] = []
    for idx, abgang in enumerate(abgaenge):
        label = str(abgang.get("label") or abgang.get("name") or f"A{idx + 1}")
        reserve = _reserve_a(abgang)
        i_max = _f(abgang.get("i_max_a"))
        last = _f(abgang.get("belastung_aktuell_a"))
        verfuegbar = _bool(abgang.get("verfuegbar_im_n1"), True) and not _bool(abgang.get("out_of_service"), False)
        if not verfuegbar or not _bool(abgang.get("koppelbar"), True):
            continue
        if reserve is None and i_max is None:
            continue
        auswertbar.append(
            {
                "label": label,
                "reserve_a": reserve,
                "i_max_a": i_max,
                "belastung_aktuell_a": last,
                "primary": _bool(abgang.get("primary")) or _bool(abgang.get("ist_anschlussabgang")),
                "datenquelle": _datenquelle(abgang.get("datenquelle")),
            }
        )

    if not auswertbar:
        return {
            "bewertung": "NICHT_GEPRUEFT",
            "primaer_abgang_label": None,
            "engpass_abgang_label": None,
            "abgaenge_gesamt": len(abgaenge),
            "abgaenge_auswertbar": 0,
            "projektstrom_a": round(projektstrom, 1),
            "beste_reserve_a": None,
            "reserve_ratio": None,
            "begruendung_technisch": "Abgangsdaten vorhanden, aber keine belastbare Reserve fuer N-1 ableitbar.",
            "begruendung_klartext": "Die vorhandenen Abgangsdaten reichen nicht, um eine Umschaltreserve belastbar zu bewerten.",
        }

    primaer = next((item for item in auswertbar if item["primary"]), None)
    if primaer is None:
        primaer = max(auswertbar, key=lambda item: _f(item.get("belastung_aktuell_a"), 0.0) or 0.0)

    alternativen = [item for item in auswertbar if item["label"] != primaer["label"]]
    if not alternativen:
        return {
            "bewertung": "ROT",
            "primaer_abgang_label": primaer["label"],
            "engpass_abgang_label": primaer["label"],
            "abgaenge_gesamt": len(abgaenge),
            "abgaenge_auswertbar": len(auswertbar),
            "projektstrom_a": round(projektstrom, 1),
            "beste_reserve_a": None,
            "reserve_ratio": None,
            "begruendung_technisch": "Nur ein auswertbarer N-1-faehiger Abgang vorhanden - keine alternative Umschaltreserve.",
            "begruendung_klartext": "Es gibt keinen zweiten belastbar auswertbaren Abgang als Reserve fuer den Anschluss.",
        }

    beste_alternative = max(alternativen, key=lambda item: _f(item.get("reserve_a"), -1.0) or -1.0)
    beste_reserve = _f(beste_alternative.get("reserve_a"))
    if beste_reserve is None:
        return {
            "bewertung": "NICHT_GEPRUEFT",
            "primaer_abgang_label": primaer["label"],
            "engpass_abgang_label": beste_alternative["label"],
            "abgaenge_gesamt": len(abgaenge),
            "abgaenge_auswertbar": len(auswertbar),
            "projektstrom_a": round(projektstrom, 1),
            "beste_reserve_a": None,
            "reserve_ratio": None,
            "begruendung_technisch": "Alternative Abgaenge vorhanden, aber deren Reserve im N-1-Fall ist nicht quantifiziert.",
            "begruendung_klartext": "Es gibt Alternativabgaenge, ihre freie Umschaltreserve ist aber nicht belastbar quantifiziert.",
        }

    reserve_ratio = beste_reserve / projektstrom if projektstrom > 0 else 999.0
    if reserve_ratio >= GRENZEN["abgang_reserve_ratio"]["gruen_min"]:
        bewertung = "GRUEN"
    elif reserve_ratio >= GRENZEN["abgang_reserve_ratio"]["gelb_min"]:
        bewertung = "GELB"
    else:
        bewertung = "ROT"

    begruendung_technisch = (
        f"N-1 Abgang: Projektstrom={projektstrom:.1f} A, beste alternative Reserve={beste_reserve:.1f} A "
        f"ueber {beste_alternative['label']} -> Reservefaktor={reserve_ratio:.2f}. "
        "Konservativ wird nur die beste einzelne alternative Reserve gewertet; "
        "verteilte Lastaufteilung wird ohne verifiziertes Umschaltkonzept nicht unterstellt."
    )

    if bewertung == "GRUEN":
        begruendung_klartext = (
            f"Ein alternativer Abgang ({beste_alternative['label']}) hat rechnerisch genug Reserve "
            f"({beste_reserve:.0f} A), um den Zubau im N-1-Fall mitzutragen."
        )
    elif bewertung == "GELB":
        begruendung_klartext = (
            f"Die beste alternative Abgangsreserve ({beste_reserve:.0f} A ueber {beste_alternative['label']}) "
            "liegt knapp am benoetigten Zubaustrom. Eine vertiefte Netzplanung ist noetig."
        )
    else:
        begruendung_klartext = (
            f"Die beste alternative Abgangsreserve ({beste_reserve:.0f} A ueber {beste_alternative['label']}) "
            "reicht fuer den Zubau nicht aus. Betriebsmittel- oder Anschlussvariante anpassen."
        )

    return {
        "bewertung": bewertung,
        "primaer_abgang_label": primaer["label"],
        "engpass_abgang_label": beste_alternative["label"],
        "abgaenge_gesamt": len(abgaenge),
        "abgaenge_auswertbar": len(auswertbar),
        "projektstrom_a": round(projektstrom, 1),
        "beste_reserve_a": round(beste_reserve, 1),
        "reserve_ratio": round(reserve_ratio, 3),
        "begruendung_technisch": begruendung_technisch,
        "begruendung_klartext": begruendung_klartext,
    }


# ----------------------------------------------------------------------
# 4. Spannung-N-1
# ----------------------------------------------------------------------
def _ist_ms_nennspannung(u_kv: float | None) -> bool:
    if u_kv is None:
        return False
    return 1.0 <= u_kv < 60.0


def bewerte_spannung_n1(
    spannung_n1: dict | None,
    nennspannung_kv: float | None = None,
) -> dict:
    """
    Spannung-N-1: delta U bei Ausfall eines Parallelsystems.
    """
    gelb_legacy = GRENZEN["spannung_n1"]["gelb_max_prozent"]

    if not spannung_n1:
        return {
            "bewertung": "NICHT_GEPRUEFT",
            "delta_u_n1_prozent": None,
            "grenze_prozent": gelb_legacy,
            "begruendung_technisch": "Keine Spannungsdaten fuer N-1-Fall.",
            "begruendung_klartext": "Spannungsaenderung im Ausfallszenario wurde nicht berechnet.",
        }

    delta = _f(spannung_n1.get("delta_u_prozent"))
    if delta is None:
        return {
            "bewertung": "NICHT_GEPRUEFT",
            "delta_u_n1_prozent": None,
            "grenze_prozent": gelb_legacy,
            "begruendung_technisch": "Delta U im N-1-Fall nicht ermittelbar.",
            "begruendung_klartext": "Die Spannungsaenderung konnte nicht ermittelt werden.",
        }

    if _ist_ms_nennspannung(nennspannung_kv):
        gruen_max = MS_SPANNUNG_N1_SCREENING["gruen_max_pct"]
        gelb_max = MS_SPANNUNG_N1_SCREENING["gelb_max_pct"]
        norm_txt = "MS N-1-Screening konsistent mit constants.THRESHOLDS (n1_delta_u_warn / n1_delta_u_crit)"
    else:
        gruen_max = GRENZEN["spannung_n1"]["gruen_max_prozent"]
        gelb_max = GRENZEN["spannung_n1"]["gelb_max_prozent"]
        norm_txt = "Legacy-Screening (5%/10%) ohne vereinheitlichte MS-Nennspannung."

    delta_abs = abs(delta)
    bewertung = _bewertung_aus_prozent(delta_abs, gruen_max, gelb_max)
    begruendung_technisch = (
        f"N-1 Spannung: |delta U_N1|={delta_abs:.2f}% "
        f"(Grenzen: GRUEN<={gruen_max}%, GELB<={gelb_max}%; {norm_txt})."
    )

    if bewertung == "GRUEN":
        begruendung_klartext = f"Spannungsaenderung im Ausfallfall {delta_abs:.1f}% - innerhalb der Screening-Grenzen."
    elif bewertung == "GELB":
        begruendung_klartext = f"Spannungsaenderung im Ausfallfall {delta_abs:.1f}% - grenzwertig, vertiefte Pruefung empfohlen."
    else:
        begruendung_klartext = (
            f"Spannungsaenderung im Ausfallfall {delta_abs:.1f}% - ueberschreitet {gelb_max}% "
            "und erfordert Spannungshaltung oder Detailpruefung."
        )

    return {
        "bewertung": bewertung,
        "delta_u_n1_prozent": round(delta_abs, 2),
        "grenze_prozent": gelb_max,
        "begruendung_technisch": begruendung_technisch,
        "begruendung_klartext": begruendung_klartext,
    }


# ----------------------------------------------------------------------
# 5. N1-Klasse + Konfidenz
# ----------------------------------------------------------------------
def bestimme_n1_klasse(
    n1_topo: dict,
    n1_leit: dict,
    n1_abgang: dict,
    n1_trafo: dict,
    n1_spg: dict,
    dso_daten_vorhanden: bool = False,
) -> str:
    """
    Klassifiziert die Tiefe der N-1-Analyse:
      N1-0: nichts geprueft
      N1-1: nur Topologie
      N1-2: + Pfad/Betriebsmittel (Leitung oder Abgang)
      N1-3: + Trafo + Spannung
      N1-4: + verifizierte Netzbetreiberdaten
    """
    topo_geprueft = _ist_geprueft(n1_topo)
    pfad_geprueft = _ist_geprueft(n1_leit) or _ist_geprueft(n1_abgang)
    trafo_geprueft = _ist_geprueft(n1_trafo)
    spannung_geprueft = _ist_geprueft(n1_spg)

    if dso_daten_vorhanden and topo_geprueft and pfad_geprueft and trafo_geprueft and spannung_geprueft:
        klasse = "N1-4"
    elif topo_geprueft and pfad_geprueft and trafo_geprueft and spannung_geprueft:
        klasse = "N1-3"
    elif topo_geprueft and pfad_geprueft:
        klasse = "N1-2"
    elif topo_geprueft:
        klasse = "N1-1"
    else:
        klasse = "N1-0"
    # MVP ohne DSO-Daten: maximal N1-2 behaupten (06-arbeitsweise-gridcheck.mdc).
    if not dso_daten_vorhanden and klasse in ("N1-3", "N1-4"):
        return "N1-2"
    return klasse


def berechne_konfidenz(n1_klasse: str, anzahl_default_annahmen: int) -> float:
    """
    Konfidenz 0.1..1.0 abhaengig von N1-Klasse und Anzahl Default-Annahmen.
    """
    basis = {
        "N1-0": 0.10,
        "N1-1": 0.30,
        "N1-2": 0.55,
        "N1-3": 0.80,
        "N1-4": 1.00,
    }.get(n1_klasse, 0.10)
    malus = 0.05 * max(0, anzahl_default_annahmen)
    konfidenz = basis - malus
    return round(max(0.10, min(1.00, konfidenz)), 2)


# ----------------------------------------------------------------------
# 6. Engpass-Komponente
# ----------------------------------------------------------------------
def _engpass(
    n1_topo: dict,
    n1_leit: dict,
    n1_abgang: dict,
    n1_trafo: dict,
    n1_spg: dict,
) -> str:
    """
    Liefert die Komponente mit der schlechtesten Bewertung.
    Abgang wird bewusst vor Leitung priorisiert, wenn eine explizite
    Betriebsmittelreserve vorhanden ist - aus Sicht des Netzplaners oft der
    konkret angreifbarere Engpass.
    """
    rang = {"GRUEN": 0, "GELB": 1, "ROT": 2}
    kandidaten = [
        ("abgang", n1_abgang.get("bewertung")),
        ("leitung", n1_leit.get("bewertung")),
        ("trafo", n1_trafo.get("bewertung")),
        ("spannung", n1_spg.get("bewertung")),
        ("topologie", n1_topo.get("bewertung")),
    ]
    aktiv = [(name, bewertung) for name, bewertung in kandidaten if bewertung in rang]
    if not aktiv:
        return "keine"
    worst = max(aktiv, key=lambda item: rang[item[1]])
    if rang[worst[1]] == 0:
        return "keine"
    return worst[0]


# ----------------------------------------------------------------------
# 7. Empfehlungen
# ----------------------------------------------------------------------
def _empfehlungen(
    n1_topo: dict,
    n1_leit: dict,
    n1_abgang: dict,
    n1_trafo: dict,
    n1_spg: dict,
    *,
    n1_klasse: str,
    dso_daten_vorhanden: bool,
) -> list[str]:
    empfehlungen: list[str] = []

    if n1_abgang.get("bewertung") == "ROT":
        empfehlungen.append("Abgangsreserve erhoehen oder alternativen Einspeise-/Reserveabgang planerisch nachweisen.")
    elif n1_abgang.get("bewertung") == "GELB":
        empfehlungen.append("Umschaltreserve des alternativen Abgangs mit realem Schaltkonzept und Lastdaten verifizieren.")

    if n1_trafo.get("bewertung") == "ROT":
        empfehlungen.append("Umspannwerk verstaerken (zusaetzlicher Trafo oder groessere Sn).")
    elif n1_trafo.get("bewertung") == "GELB":
        empfehlungen.append("Trafo-Ueberlastreserve mit dem Netzbetreiber klaeren (Zeitdauer, Notbetrieb, Kuehlreserve).")

    if n1_leit.get("bewertung") == "ROT":
        empfehlungen.append("Groesseren Kabelquerschnitt oder zusaetzliches Parallelsystem pruefen.")
    elif n1_leit.get("bewertung") == "GELB":
        empfehlungen.append("Leitung im N-1-Fall grenzwertig - Betriebsfuehrung und Lastmanagement nachweisen.")

    if n1_spg.get("bewertung") == "ROT":
        empfehlungen.append("Spannungshaltung absichern (Q(U)-Regelung, Stufensteller, Kompensation).")
    elif n1_spg.get("bewertung") == "GELB":
        empfehlungen.append("Q(U)-Statik und Spannungsband im Stoerungsfall mit dem Netzbetreiber abstimmen.")

    if n1_topo.get("bewertung") == "ROT":
        empfehlungen.append("Topologie ungeeignet - Ringeinbindung, zweite Einspeisung oder Notverbindung pruefen.")

    if n1_klasse == "N1-1":
        empfehlungen.append("Fuer die naechste Stufe mindestens Abgangs- oder Leitungsreserve im N-1-Fall nachweisen.")
    elif n1_klasse == "N1-2":
        empfehlungen.append("Fuer eine belastbarere N-1-Aussage Traforeserve und Spannungsnachweis im Stoerungsfall ergaenzen.")

    if not dso_daten_vorhanden:
        empfehlungen.append("Verifizierte Netzbetreiberdaten einholen; ohne diese bleibt das N-1-Screening konservativ vorlaeufig.")

    if not empfehlungen:
        empfehlungen.append("Keine kritischen N-1-Verstoesse - Anschluss netzseitig im Screening technisch plausibel.")
    return empfehlungen


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def analysiere_n1(
    eingabe: dict,
    thermisch_n1: dict | None = None,
    spannung_n1: dict | None = None,
    zusatzlast_mw: float | None = None,
) -> dict:
    """
    Hauptfunktion: vollstaendige N-1-Analyse.
    """
    eingabe = eingabe or {}

    p_mw = _f(zusatzlast_mw if zusatzlast_mw is not None else eingabe.get("leistung_mw"), 0.0) or 0.0
    u_nenn = _f(eingabe.get("nennspannung"))
    cos_phi = _f(eingabe.get("cos_phi"), 0.95) or 0.95
    projektstrom_a = _zusatzstrom_a(p_mw, cos_phi, u_nenn)
    dso_daten_vorhanden = _ist_dso_verifiziert(eingabe)

    n1_topo = bewerte_n1_ms(
        {
            "topologie": eingabe.get("topologie"),
            "leistung_mw": eingabe.get("leistung_mw"),
            "cos_phi": eingabe.get("cos_phi"),
            "restkapazitaet_ms_mva": eingabe.get("restkapazitaet_ms_mva"),
            "umschaltzeit_min": eingabe.get("umschaltzeit_min"),
        }
    )
    n1_leit = bewerte_leitung_n1(thermisch_n1)
    n1_abgang = bewerte_abgang_n1(eingabe, projektstrom_a)
    n1_trafo = bewerte_trafo_n1(eingabe.get("umspannwerk"), p_mw, cos_phi)
    n1_spg = bewerte_spannung_n1(spannung_n1, nennspannung_kv=u_nenn)

    annahmen: list[dict[str, Any]] = []
    if not eingabe.get("umspannwerk"):
        annahmen.append(
            {
                "feld": "umspannwerk",
                "wert": None,
                "quelle": "default",
                "begruendung": "Keine Umspannwerksdaten - Trafo-N-1 nicht pruefbar (max. N1-2/N1-3 ohne belastbaren Trafo-Nachweis).",
            }
        )
    if eingabe.get("topologie") in (None, "unbekannt", ""):
        annahmen.append(
            {
                "feld": "topologie",
                "wert": eingabe.get("topologie"),
                "quelle": "default",
                "begruendung": "Topologie unbekannt - konservativ nur heuristische N-1-Aussage moeglich.",
            }
        )
    if eingabe.get("restkapazitaet_ms_mva") is None:
        annahmen.append(
            {
                "feld": "restkapazitaet_ms_mva",
                "wert": None,
                "quelle": "default",
                "begruendung": "Keine Restkapazitaet bekannt - topologische N-1-Faehigkeit bleibt ohne Netzdaten nur bedingt plausibel.",
            }
        )
    if not _extrahiere_abgaenge(eingabe):
        annahmen.append(
            {
                "feld": "abgaenge",
                "wert": None,
                "quelle": "default",
                "begruendung": "Keine Abgangsdaten vorhanden - Umschalt-/Betriebsmittelreserve nur indirekt ueber Leitungs-Screening bewertet.",
            }
        )
    if not dso_daten_vorhanden:
        annahmen.append(
            {
                "feld": "n1_datengrundlage",
                "wert": eingabe.get("n1_datengrundlage"),
                "quelle": "default",
                "begruendung": "Keine verifizierten Netzbetreiberdaten - Screening bleibt konservativ vorlaeufig und erreicht maximal N1-2.",
            }
        )

    n_default = sum(1 for item in annahmen if item["quelle"] == "default")
    n1_klasse = bestimme_n1_klasse(
        n1_topo,
        n1_leit,
        n1_abgang,
        n1_trafo,
        n1_spg,
        dso_daten_vorhanden=dso_daten_vorhanden,
    )
    konfidenz = berechne_konfidenz(n1_klasse, n_default)
    stufenbegruendung = _stufenbegruendung(n1_klasse, dso_daten_vorhanden=dso_daten_vorhanden)
    nachweise_vorhanden, nachweise_fehlend = _nachweise(
        n1_topo,
        n1_leit,
        n1_abgang,
        n1_trafo,
        n1_spg,
        dso_daten_vorhanden=dso_daten_vorhanden,
    )
    empfehlungen = _empfehlungen(
        n1_topo,
        n1_leit,
        n1_abgang,
        n1_trafo,
        n1_spg,
        n1_klasse=n1_klasse,
        dso_daten_vorhanden=dso_daten_vorhanden,
    )
    engpass = _engpass(n1_topo, n1_leit, n1_abgang, n1_trafo, n1_spg)
    gesamt_bewertung = _max_bewertung(
        n1_topo.get("bewertung"),
        n1_leit.get("bewertung"),
        n1_abgang.get("bewertung"),
        n1_trafo.get("bewertung"),
        n1_spg.get("bewertung"),
    )

    return {
        "n1_topologie": n1_topo,
        "n1_leitung": n1_leit,
        "n1_abgang": n1_abgang,
        "n1_trafo": n1_trafo,
        "n1_spannung": n1_spg,
        "gesamt": {
            "bewertung": gesamt_bewertung,
            "engpass_komponente": engpass,
            "n1_klasse": n1_klasse,
            "konfidenz": konfidenz,
            "stufenbegruendung": stufenbegruendung,
            "dso_daten_vorhanden": dso_daten_vorhanden,
            "empfehlungen": empfehlungen,
            "nachweise_vorhanden": nachweise_vorhanden,
            "nachweise_fehlend": nachweise_fehlend,
        },
        "annahmen": annahmen,
        "berechnungs_version": VERSION,
        "backend": BACKEND,
    }
