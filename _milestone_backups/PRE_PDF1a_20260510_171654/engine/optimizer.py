"""
engine/optimizer.py - Deterministische Leistungsoptimierung.

Berechnet die maximal zulaessige Anlagenleistung (P_max) basierend auf
linearer Skalierung der Engpass-Groessen aus dem Engine-Ergebnis.

Annahmen (physikalisch begruendet):
  - Trafo-Auslastung skaliert linear mit P (S = P/cos_phi).
  - Spannungsanhebung Delta_u skaliert linear mit P (festes cos_phi, R/X).
  - Leitungsstrom I skaliert linear mit P.
  - Kurzschluss-Verhaeltnis Sk/Sn skaliert invers linear mit P (Sk fest).

Grenzwerte (konservativ, VDE-AR-N 4110/4120):
  - Trafo:        100 %
  - Spannung:     delta_u_hartgrenze_pct (aus Engine, default 3 %)
  - Thermisch:    100 %
  - Kurzschluss:  Sk/Sn >= 10  (typische Mindestanforderung MS)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Schwellen
TRAFO_MAX_PCT = 100.0
THERM_MAX_PCT = 100.0
SK_SN_MIN = 10.0


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _p_max_trafo(result: Dict[str, Any], p_ist_mw: float) -> Optional[float]:
    t = result.get("trafo") or {}
    a = _safe_float(t.get("auslastung_prozent"))
    if a is None or a <= 0 or p_ist_mw <= 0:
        return None
    return p_ist_mw * (TRAFO_MAX_PCT / a)


def _p_max_spannung(result: Dict[str, Any], p_ist_mw: float) -> Optional[float]:
    s = result.get("spannung") or {}
    du = _safe_float(s.get("delta_u_prozent"))
    grenze = _safe_float(s.get("delta_u_hartgrenze_pct")) or 3.0
    if du is None or du <= 0 or p_ist_mw <= 0:
        return None
    return p_ist_mw * (grenze / du)


def _p_max_thermisch(result: Dict[str, Any], p_ist_mw: float) -> Optional[float]:
    th = result.get("thermisch") or {}
    a = _safe_float(th.get("auslastung_prozent"))
    if a is None or a <= 0 or p_ist_mw <= 0:
        return None
    return p_ist_mw * (THERM_MAX_PCT / a)


def _p_max_kurzschluss(result: Dict[str, Any], p_ist_mw: float) -> Optional[float]:
    k = result.get("kurzschluss") or {}
    ratio = _safe_float(k.get("sk_sn_ratio"))
    if ratio is None or ratio <= 0 or p_ist_mw <= 0:
        return None
    # ratio = Sk/Sn, Sn ~ P -> P_max = P_ist * (ratio / SK_SN_MIN)
    return p_ist_mw * (ratio / SK_SN_MIN)


def _engpass_text(result: Dict[str, Any]) -> List[str]:
    out = []
    t = result.get("trafo") or {}
    if (_safe_float(t.get("auslastung_prozent")) or 0) > TRAFO_MAX_PCT:
        out.append(f"Trafo {t.get('auslastung_prozent')} %")
    s = result.get("spannung") or {}
    grenze = _safe_float(s.get("delta_u_hartgrenze_pct")) or 3.0
    if (_safe_float(s.get("delta_u_prozent")) or 0) > grenze:
        out.append(f"Spannung {s.get('delta_u_prozent')} % (>{grenze} %)")
    th = result.get("thermisch") or {}
    if (_safe_float(th.get("auslastung_prozent")) or 0) > THERM_MAX_PCT:
        out.append(f"Thermisch {th.get('auslastung_prozent')} %")
    k = result.get("kurzschluss") or {}
    ratio = _safe_float(k.get("sk_sn_ratio"))
    if ratio is not None and ratio < SK_SN_MIN:
        out.append(f"Sk/Sn {ratio} (<{SK_SN_MIN})")
    return out


def optimiere(
    result: Dict[str, Any],
    eingabe: Dict[str, Any],
    constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Berechnet max. zulaessige Leistung und Varianten.

    Args:
        result:     Engine-Ergebnis (komplettes dict).
        eingabe:    Original-Eingabe (fuer p_ist).
        constraints: Projektierer-Constraints (flex_leistung etc.).

    Returns:
        Optimizer-Block fuer projektierer-Antwort.
    """
    constraints = constraints or {}

    p_ist_mw = _safe_float(eingabe.get("leistung_mw"))
    if p_ist_mw is None:
        p_kw = _safe_float(eingabe.get("p_kw"))
        p_ist_mw = (p_kw / 1000.0) if p_kw else None

    if not p_ist_mw or p_ist_mw <= 0:
        return {
            "status": "ERROR",
            "hinweis": "Keine gueltige Leistung im Input gefunden.",
        }

    fazit = result.get("fazit", {})
    fazit_kennung = fazit.get("kennung") if isinstance(fazit, dict) else None

    # Wenn Engine bereits OK (A/B), keine Reduktion noetig
    if fazit_kennung in ("A",):
        return {
            "status": "OK",
            "p_ist_mw": p_ist_mw,
            "p_max_mw": p_ist_mw,
            "engpaesse": [],
            "varianten": [],
            "empfehlung": "Anschluss in aktueller Auslegung machbar (Fazit A).",
        }

    # P_max je Engpass
    kandidaten = {
        "trafo": _p_max_trafo(result, p_ist_mw),
        "spannung": _p_max_spannung(result, p_ist_mw),
        "thermisch": _p_max_thermisch(result, p_ist_mw),
        "kurzschluss": _p_max_kurzschluss(result, p_ist_mw),
    }
    valide = {k: v for k, v in kandidaten.items() if v is not None and v > 0}

    if not valide:
        return {
            "status": "UNKLAR",
            "p_ist_mw": p_ist_mw,
            "hinweis": "Keine Engpass-Kennzahlen auswertbar.",
        }

    bindender_engpass = min(valide, key=valide.get)
    p_max_mw = round(valide[bindender_engpass], 3)

    # Varianten
    varianten: List[Dict[str, Any]] = []

    # Variante 1: Reduktion auf P_max
    flex_leistung = bool(constraints.get("flex_leistung", False))
    varianten.append({
        "name": "Reduktion auf P_max",
        "leistung_mw": p_max_mw,
        "reduktion_prozent": round(100.0 * (1 - p_max_mw / p_ist_mw), 1),
        "machbar": True,
        "voraussetzung": None if flex_leistung else "Constraint flex_leistung=true erforderlich",
    })

    # Variante 2: Q-Regelung (nur sinnvoll wenn Spannung der bindende Engpass)
    if bindender_engpass == "spannung":
        # Konservativ: Q-Regelung erlaubt ~30 % mehr P bei Spannungsproblemen
        p_q = min(round(p_max_mw * 1.3, 3), p_ist_mw)
        varianten.append({
            "name": "Mit Q-Regelung (cos phi 0.95 untererregt)",
            "leistung_mw": p_q,
            "reduktion_prozent": round(100.0 * (1 - p_q / p_ist_mw), 1),
            "machbar": True,
            "auflage": "Blindleistungsregelung gem. VDE-AR-N 4110",
            "hinweis": "Indikative Abschaetzung; finale Pruefung durch Netzbetreiber.",
        })

    # Variante 3: Netzausbau (immer als Option, wenn nicht flex)
    varianten.append({
        "name": "Netzausbau / Trafo-Verstaerkung",
        "leistung_mw": p_ist_mw,
        "reduktion_prozent": 0.0,
        "machbar": None,  # haengt vom NB ab
        "hinweis": "Ausbaubedarf vom Netzbetreiber pruefen lassen.",
    })

    # Empfehlung
    if flex_leistung:
        empfehlung = f"Variante 1 empfohlen: Reduktion auf {p_max_mw} MW (bindender Engpass: {bindender_engpass})."
    else:
        empfehlung = f"Ohne Leistungsflexibilitaet: Netzausbau pruefen. Sonst Reduktion auf {p_max_mw} MW noetig."

    return {
        "status": "OK",
        "p_ist_mw": p_ist_mw,
        "p_max_mw": p_max_mw,
        "bindender_engpass": bindender_engpass,
        "engpaesse": _engpass_text(result),
        "p_max_je_engpass_mw": {k: round(v, 3) for k, v in valide.items()},
        "varianten": varianten,
        "empfehlung": empfehlung,
        "annahmen": {
            "trafo_max_pct": TRAFO_MAX_PCT,
            "thermisch_max_pct": THERM_MAX_PCT,
            "sk_sn_min": SK_SN_MIN,
            "skalierung": "linear in P (cos_phi, R/X konstant)",
        },
    }
