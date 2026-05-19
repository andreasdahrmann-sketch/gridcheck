"""
Conservative engine helpers — transparency-first, no fake capacity claims.
"""
from __future__ import annotations

import math
import re
from typing import Any


def _bestimme_spannungsebene(u_kv: float) -> str:
    if u_kv >= 60:
        return "HS"
    if u_kv >= 1:
        return "MS"
    return "NS"


# Typical indicative connection-power bands (screening hints, not permits).
POWER_LIMIT_HINTS_KW = {
    "NS": {
        "label": "Niederspannung (≤ 1 kV)",
        "typical_max_kw": 135,
        "screening_upper_kw": 300,
        "hinweis": (
            "Über ca. 135 kW Einspeiseleistung ist in der Regel ein MS-Anschluss zu prüfen "
            "(VDE-AR-N 4105 / Netzbetreiber-TAB können strenger sein)."
        ),
    },
    "MS": {
        "label": "Mittelspannung (> 1 kV bis 35 kV)",
        "typical_max_kw": 20_000,
        "screening_upper_kw": 50_000,
        "hinweis": (
            "Großanlagen und systemrelevante Einspeisung erfordern N-1-/Netzstudien mit "
            "verifizierten Netzbetreiberdaten; MVP-Screening bleibt maximal N1-2 ohne DSO-Daten."
        ),
    },
    "HS": {
        "label": "Hochspannung (> 35 kV)",
        "typical_max_kw": 100_000,
        "screening_upper_kw": 200_000,
        "hinweis": (
            "HS-Anschlüsse sind projektspezifisch; Kurzschluss- und N-1-Nachweise sind ohne "
            "VNB-Netzdaten nur vorläufig."
        ),
    },
}

# Conservative short-circuit current bands (kA) when Sk'' is not verified — not a capacity claim.
IK_BAND_KA = {
    "NS": {"min": 16.0, "typ": 22.0, "max": 25.0},
    "MS": {"min": 20.0, "typ": 25.0, "max": 31.5},
    "HS": {"min": 31.5, "typ": 40.0, "max": 63.0},
}

CABLE_LENGTH_KM_BY_LEVEL = {
    "NS": (0.15, 2.5),
    "MS": (1.0, 12.0),
    "HS": (5.0, 35.0),
}

COS_PHI_DEFAULTS = {
    "pv": 1.0,
    "wind": 1.0,
    "solar": 1.0,
    "bess": 0.92,
    "battery": 0.92,
    "speicher": 0.92,
    "charging": 0.95,
    "load": 0.95,
    "entnahme": 0.95,
    "einspeisung": 1.0,
    "hybrid": 0.98,
    "default": 0.95,
}


def _f(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        parsed = float(value)
        return parsed
    except (TypeError, ValueError):
        return default


def _normalize_anlagentyp(eingabe: dict) -> str:
    raw = str(eingabe.get("anlagentyp") or "").strip().lower()
    components = eingabe.get("project_components") or []
    if isinstance(components, list) and components:
        types = {
            str(item.get("component_type") or "").strip().lower()
            for item in components
            if isinstance(item, dict)
        }
        if "battery" in types or "bess" in types:
            if len(types) > 1:
                return "hybrid"
            return "bess"
        if "pv" in types or "wind" in types:
            return "pv"
    return raw or "default"


def estimate_cable_length_km(eingabe: dict) -> dict[str, Any]:
    """
    Heuristic cable route length — never presented as measured GPS distance.
    """
    existing = _f(eingabe.get("entfernung_km"))
    if existing is not None and 0 < existing <= 500:
        return {
            "entfernung_km": round(existing, 3),
            "quelle": "nutzer",
            "heuristisch": False,
            "annahme": "Trassenentfernung wurde vom Nutzer vorgegeben.",
        }

    u_kv = _f(eingabe.get("nennspannung"), 20.0) or 20.0
    ebene = _bestimme_spannungsebene(u_kv)
    low, high = CABLE_LENGTH_KM_BY_LEVEL.get(ebene, CABLE_LENGTH_KM_BY_LEVEL["MS"])

    plz = re.sub(r"\D", "", str(eingabe.get("plz") or ""))[:5]
    plz_offset = (int(plz) % 97) / 97.0 if plz else 0.5

    loc = eingabe.get("project_location")
    coord_jitter = 0.0
    if isinstance(loc, dict):
        lat = _f(loc.get("latitude"))
        lon = _f(loc.get("longitude"))
        if lat is not None and lon is not None:
            # Deterministic spread only — not geodesic distance to a grid asset.
            coord_jitter = (abs(lat * 1000.0) + abs(lon * 1000.0)) % 1.0

    span = high - low
    km = low + span * (0.35 * plz_offset + 0.15 * coord_jitter)
    km = round(max(low, min(high, km)), 3)

    return {
        "entfernung_km": km,
        "quelle": "heuristik",
        "heuristisch": True,
        "annahme": (
            f"Trassenentfernung {km} km ist eine heuristische Schätzung nach Spannungsebene {ebene} "
            "(typischer Korridor {low}–{high} km). Keine GPS-/Luftlinienmessung zum Netzanschlusspunkt."
        ).format(low=low, high=high),
    }


def resolve_cos_phi_for_calculation(eingabe: dict) -> dict[str, Any]:
    """Use explicit cos φ or role-based conservative default with documented assumption."""
    explicit = _f(eingabe.get("cos_phi"))
    if explicit is not None and 0.8 <= explicit <= 1.0:
        return {
            "cos_phi": round(explicit, 4),
            "quelle": "nutzer",
            "annahme": f"cos φ = {explicit} aus Projekteingabe.",
        }

    typ = _normalize_anlagentyp(eingabe)
    anschluss = str(eingabe.get("anschlussart") or "").strip()
    if anschluss == "Entnahme":
        typ = "entnahme"
    elif anschluss == "Einspeisung":
        typ = typ if typ not in ("", "default") else "einspeisung"

    default = COS_PHI_DEFAULTS.get(typ, COS_PHI_DEFAULTS["default"])
    return {
        "cos_phi": default,
        "quelle": "rolle_default",
        "annahme": (
            f"cos φ = {default} als konservativer Standardwert für Anlagentyp '{typ}' "
            "(keine explizite Eingabe). Spannungsfall und Scheinleistung sind damit vorläufig."
        ),
    }


def get_max_short_circuit_current_ka(
    spannungsebene: str,
    *,
    sk_mva_user: float | None = None,
    ik_berechnet_ka: float | None = None,
) -> dict[str, Any]:
    """
    Conservative Ik bands by voltage level. Marked vorläufig without verified Sk'' from DSO.
    """
    ebene = spannungsebene if spannungsebene in IK_BAND_KA else "MS"
    band = IK_BAND_KA[ebene]
    vorlaeufig = sk_mva_user is None

    referenz_ka = band["typ"]
    if ik_berechnet_ka is not None and ik_berechnet_ka > 0:
        # Do not report unrealistically low Ik when impedance model is weak — stay within band.
        referenz_ka = max(band["min"], min(band["max"], ik_berechnet_ka))

    return {
        "ik_referenz_ka": round(referenz_ka, 2),
        "ik_band_min_ka": band["min"],
        "ik_band_typ_ka": band["typ"],
        "ik_band_max_ka": band["max"],
        "vorlaeufig": vorlaeufig,
        "hinweis": (
            "Vorläufige Ik-Bandbreite nach Spannungsebene; verbindlich ist Sk'' aus der Netzbetreiber-Auskunft."
            if vorlaeufig
            else "Ik-Bewertung nutzt angegebene Sk''-Angabe; Bandbreite dient zum Abgleich."
        ),
    }


def kosten_leistungs_staffel_faktor(p_mw: float, spannungsebene: str) -> dict[str, Any]:
    """
    Tiered cost multiplier by plant size — avoids flat capping at 500 kW for large projects.
    """
    p_kw = max(0.0, p_mw * 1000.0)
    if spannungsebene == "NS":
        tiers = [
            (100, 1.0),
            (500, 1.12),
            (1_500, 1.28),
            (5_000, 1.45),
            (float("inf"), 1.6),
        ]
    elif spannungsebene == "HS":
        tiers = [
            (5_000, 1.0),
            (20_000, 1.18),
            (50_000, 1.35),
            (150_000, 1.55),
            (float("inf"), 1.75),
        ]
    else:
        tiers = [
            (500, 1.0),
            (2_000, 1.1),
            (10_000, 1.25),
            (30_000, 1.42),
            (float("inf"), 1.58),
        ]

    faktor = tiers[-1][1]
    stufe_label = "sehr_gross"
    for limit_kw, tier_factor in tiers:
        if p_kw <= limit_kw:
            faktor = tier_factor
            if limit_kw <= 500:
                stufe_label = "klein"
            elif limit_kw <= 2_000:
                stufe_label = "mittel"
            elif limit_kw <= 10_000:
                stufe_label = "gross"
            else:
                stufe_label = "sehr_gross"
            break

    return {
        "faktor": round(faktor, 3),
        "stufe": stufe_label,
        "leistung_kw": round(p_kw, 1),
        "annahme": (
            f"Kostenstaffel '{stufe_label}' für {round(p_kw, 0):.0f} kW auf {spannungsebene} "
            f"(Multiplikator {faktor:.2f} auf Stations-/Schutzbasis — Bandbreite, keine Angebotssumme)."
        ),
    }


def erzeuge_blindleistung_trafo_warnungen(
    eingabe: dict,
    trafo: dict | None,
    pqs: dict | None,
    leitungstyp: str | None = None,
) -> list[str]:
    """Warnings when reactive power / transformer detail is not modeled — no fake Q calculation."""
    warnings: list[str] = []
    pqs = pqs or {}
    trafo = trafo or {}

    if not eingabe.get("blindleistung_modus") and not eingabe.get("q_mvar"):
        warnings.append(
            "Blindleistung (Q) und detaillierte Trafo-/Kompensationsauslegung sind in diesem Lauf "
            "nicht modelliert — nur P/cos φ-basierte Scheinleistung. §9 EEG / VNB-Vorgaben separat prüfen."
        )

    if str(eingabe.get("anschlussart") or "") == "Einspeisung" and _f(pqs.get("q_mvar"), 0) == 0:
        warnings.append(
            "Q=0 aus cos φ nahe 1: Spannungsanhebung und Blindleistungsführung am Anschluss "
            "können dennoch relevant sein — keine automatische Netzverträglichkeitsaussage."
        )

    lt = leitungstyp or eingabe.get("leitungstyp")
    if lt and trafo.get("auslastung_prozent", 0) > 85:
        warnings.append(
            "Trafoauslastung hoch — detaillierte Trafo-/N-1-Reserve und ggf. Kompensation "
            "sind nicht vollständig berechnet, nur gescreent."
        )

    storage = eingabe.get("storage_profile")
    if isinstance(storage, dict) and storage.get("has_storage") and not storage.get("reactive_power_capable"):
        warnings.append(
            "Speicher ohne modellierte Blindleistungsfähigkeit: netzdienliche Q-Unterstützung "
            "wird nicht berechnet, nur als Projektmerkmal geführt."
        )

    return warnings


def n1_mvp_dokumentation(eingabe: dict, n1_klasse: str | None) -> dict[str, Any]:
    """Document N-1 screening depth for results/transparency (max N1-2 without DSO)."""
    u_kv = _f(eingabe.get("nennspannung"))
    ebene = _bestimme_spannungsebene(u_kv) if u_kv else "MS"
    p_mw = _f(eingabe.get("leistung_mw"), 0.0) or 0.0
    dso = str(eingabe.get("n1_datengrundlage") or "").lower() == "dso_verified"

    return {
        "n1_klasse": n1_klasse or "N1-0",
        "mvp_max_klasse_ohne_dso": "N1-2",
        "dso_daten_vorhanden": dso,
        "spannungsebene": ebene,
        "leistung_mw": round(p_mw, 3),
        "ms_screening_aktiv": ebene == "MS" or p_mw >= 2.0,
        "hinweis": (
            "N-1-Screening im MVP maximal N1-2 ohne verifizierte Netzbetreiberdaten; "
            "keine garantierte Versorgungssicherheit. "
            + (
                f"MS-Anlage mit {p_mw:.2f} MW: Topologie-, Leitungs- und Abgangsreserve werden "
                "trotzdem konservativ gescreent (nicht nur Kleinstanlagen < 2 MW)."
                if ebene == "MS" or p_mw >= 2.0
                else "Für MS/HS-Anlagen zusätzlich VNB-Topologie und Restkapazität einholen."
            )
        ),
    }


def erzeuge_technische_details(
    eingabe: dict,
    *,
    spannung: dict,
    kurzschluss: dict,
    leitungstyp: str,
    leitung_meta: dict | None,
    cos_phi_info: dict,
    cable_info: dict,
    ik_info: dict,
) -> dict[str, Any]:
    lt_data = leitung_meta or {}
    return {
        "spannungsfall": {
            "delta_u_prozent": spannung.get("delta_u_prozent"),
            "richtung": spannung.get("richtung"),
            "bewertung": spannung.get("bewertung"),
            "cos_phi": cos_phi_info.get("cos_phi"),
            "cos_phi_quelle": cos_phi_info.get("quelle"),
            "cos_phi_annahme": cos_phi_info.get("annahme"),
        },
        "kurzschluss": {
            "ik_max_ka": kurzschluss.get("ik_max_ka"),
            "ik_min_ka": kurzschluss.get("ik_min_ka"),
            "sk_mva": kurzschluss.get("sk_mva"),
            "ik_referenz_ka": ik_info.get("ik_referenz_ka"),
            "ik_band_min_ka": ik_info.get("ik_band_min_ka"),
            "ik_band_max_ka": ik_info.get("ik_band_max_ka"),
            "vorlaeufig": ik_info.get("vorlaeufig", True),
            "hinweis": ik_info.get("hinweis"),
        },
        "leitung": {
            "typ": leitungstyp,
            "querschnitt_mm2": lt_data.get("querschnitt"),
            "material": lt_data.get("material"),
            "i_max_a": lt_data.get("i_max"),
        },
        "trasse": {
            "entfernung_km": cable_info.get("entfernung_km"),
            "heuristisch": cable_info.get("heuristisch", False),
            "annahme": cable_info.get("annahme"),
        },
    }


def power_limit_hints(spannungsebene: str, anschlussleistung_kw: float | None = None) -> dict[str, Any]:
    spec = POWER_LIMIT_HINTS_KW.get(spannungsebene, POWER_LIMIT_HINTS_KW["MS"])
    kw = anschlussleistung_kw if anschlussleistung_kw is not None else 0.0
    over_typical = kw > spec["typical_max_kw"] if kw > 0 else False
    return {
        **spec,
        "eingabe_kw": kw,
        "ueber_typischem_richtwert": over_typical,
    }
