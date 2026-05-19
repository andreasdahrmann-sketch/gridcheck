"""
Projektierer-specific structured outputs (heuristic, non-binding).

NVP, BKZ, process timeline, TAB disclaimer — no DSO capacity claims.
"""
from __future__ import annotations

from typing import Any, Literal

from engine.fachliche_hilfen import estimate_cable_length_km
from engine.grid_calculation_types import GridConnectionInput
from engine.plant_types import PlantContext, REACTIVE_POWER_SCREENING_KW, resolve_plant_context

RiskBand = Literal["niedrig", "mittel", "hoch", "unbekannt"]


def build_tab_disclaimer(
    eingabe: dict[str, Any],
    *,
    vnb_name: str | None = None,
) -> dict[str, Any]:
    plz = str(eingabe.get("plz") or "").strip()
    applicable = bool(plz)
    vnb = vnb_name or eingabe.get("netzbetreiber")
    text = (
        "TAB des zuständigen Verteilnetzbetreibers (VNB) prüfen — Abweichungen von "
        "Richtwerten (Spannungsfall, cos φ, Schutz, Einspeisemanagement) sind üblich "
        "und können strenger sein als diese Vorprüfung."
    )
    if vnb:
        text = f"{text} Kandidat-VNB: {vnb}."
    return {
        "applicable": applicable,
        "plz": plz or None,
        "vnb_name": str(vnb) if vnb else None,
        "message": text,
        "disclaimer": (
            "PLZ→VNB-Zuordnung ist ein Kandidat aus öffentlichen Quellen, nicht verbindlich. "
            "Maßgeblich sind die Technischen Anschlussbedingungen (TAB) des zuständigen VNB."
        ),
    }


def build_process_timeline(
    input_data: GridConnectionInput,
    *,
    projektreife: str | None = None,
) -> dict[str, Any]:
    """Structured process timeline (weeks bands) — planning aid only."""
    kw = input_data.power_kw
    vl = input_data.voltage_level

    if vl == "high" or kw >= 20_000:
        total = "12-24 Wochen (HS / Großanlage, Systemstudie)"
        phases = [
            {"phase": "Vorabstimmung VNB", "duration_weeks": "2-4", "responsible": "planner"},
            {"phase": "Netzverträglichkeits- / N-1-Studie", "duration_weeks": "6-12", "responsible": "network_operator"},
            {"phase": "Anschlussbegehren & Genehmigung", "duration_weeks": "4-8", "responsible": "applicant"},
        ]
    elif vl == "medium" or kw > 100:
        total = "8-16 Wochen (MS-Anschluss, inkl. Systemstudie)"
        phases = [
            {"phase": "SNAP / Voranfrage VNB", "duration_weeks": "2-3", "responsible": "applicant"},
            {"phase": "Technische Prüfung / ONT", "duration_weeks": "4-8", "responsible": "network_operator"},
            {"phase": "Anschlussvertrag & Bauphase", "duration_weeks": "2-5", "responsible": "planner"},
        ]
    else:
        total = "4-8 Wochen (NS-Standardanschluss)"
        phases = [
            {"phase": "Anmeldung / Formulare", "duration_weeks": "1-2", "responsible": "applicant"},
            {"phase": "VNB-Prüfung NS", "duration_weeks": "2-4", "responsible": "network_operator"},
            {"phase": "Inbetriebnahme / Zähler", "duration_weeks": "1-2", "responsible": "planner"},
        ]

    if projektreife == "baubereit":
        for item in phases:
            item["note"] = "Projektreife baubereit — Zeitachse ab Antragstellung, Vorarbeiten ggf. abgeschlossen."

    return {
        "estimated_total": total,
        "phases": phases,
        "disclaimer": (
            "Zeitangaben sind Erfahrungsbänder ohne verbindliche VNB-Zusage. "
            "Fehlende Daten, TAB-Sonderwege und Engpässe können deutlich verlängern."
        ),
    }


def build_bkz_hint(
    input_data: GridConnectionInput,
    *,
    spannungsebene: str | None = None,
) -> dict[str, Any]:
    """
    Qualitative Baukostenzuschuss (BKZ) band per §25 NAV — no exact BKZ without DSO data.
    """
    kw = input_data.power_kw
    ebene = spannungsebene or {"low": "NS", "medium": "MS", "high": "HS"}.get(
        input_data.voltage_level, "MS"
    )

    if ebene == "NS" and kw <= 30:
        band: RiskBand = "niedrig"
        hint = (
            "Kleine NS-Einspeisung: BKZ typischerweise gering bis moderat — "
            "exakte Höhe nur mit VNB-Kostenschätzung (§25 NAV)."
        )
    elif ebene == "NS" or kw <= 500:
        band = "mittel"
        hint = (
            "NS-/kleine MS-Anlage: BKZ-Bandbreite mittel — Stations- und Kabelanteil "
            "dominieren; NAV-BKZ nur qualitativ ohne VNB-Angebot."
        )
    elif kw <= 5_000:
        band = "mittel"
        hint = (
            "Mittlere Großanlage: BKZ und Netzverstärkung oft wesentlicher Kostenblock — "
            "frühzeitige VNB-Kostenschätzung einplanen."
        )
    else:
        band = "hoch"
        hint = (
            "Großanlage / MS+: BKZ-Risiko hoch — Netzverstärkung, Umspannwerk oder "
            "Trassen können den BKZ-Anteil übersteigen."
        )

    return {
        "applicable": True,
        "qualitative_band": band,
        "norm_reference": "§25 NAV (Baukostenzuschuss)",
        "hint": hint,
        "disclaimer": (
            "Keine exakte BKZ-Berechnung ohne VNB-Netzverstärkungsplan und Kostenschätzung. "
            "Band dient nur der Vorplanung."
        ),
    }


def build_nvp_recommendation(
    eingabe: dict[str, Any],
    input_data: GridConnectionInput,
    *,
    plant_ctx: PlantContext | None = None,
) -> dict[str, Any]:
    """
    Heuristic NVP suggestion from location / cable estimate — not a binding DSO point.
    """
    ctx = plant_ctx or resolve_plant_context(eingabe)
    cable = estimate_cable_length_km(eingabe)
    loc = eingabe.get("project_location")
    has_geo = isinstance(loc, dict) and loc.get("latitude") is not None

    vl_label = {"low": "NS (≤1 kV)", "medium": "MS (20 kV typ.)", "high": "HS"}.get(
        input_data.voltage_level, "MS"
    )

    node_hint = "nächster öffentlicher Netzknoten (Umspannwerk / MS-Schaltanlage)"
    if has_geo:
        node_hint = (
            "nächster plausibler Netzknoten aus Geo/Netzplan-Hinweis "
            "(kein vermessener NVP)"
        )

    flaeche_ha = eingabe.get("flaeche_ha")
    cable_note = f"geschätzte Kabellänge ca. {cable['entfernung_km']} km ({cable['quelle']})"
    if flaeche_ha:
        try:
            ha = float(flaeche_ha)
            if ha > 0:
                cable_note += f"; Fläche {ha} ha als Trassen-Hinweis (keine Vermessung)"
        except (TypeError, ValueError):
            pass

    return {
        "applicable": True,
        "suggested_voltage_level": vl_label,
        "nearest_node_hint": node_hint,
        "cable_length_estimate_km": cable["entfernung_km"],
        "cable_length_note": cable_note,
        "plant_type": ctx.plant_type.value,
        "ac_kw": ctx.ac_kw,
        "disclaimer": (
            "NVP-Empfehlung ist heuristisch und ersetzt keine Netzanschlussbegehren des VNB. "
            "Verbindlicher Netzanschlusspunkt wird erst vom Verteilnetzbetreiber festgelegt."
        ),
    }


def build_kumulation_warning() -> dict[str, Any]:
    return {
        "applicable": True,
        "message": (
            "Kumulations-Check: Diese Analyse betrachtet nur den einzelnen Projektanschluss. "
            "Aggregierte Einspeisung am Ortsnetztransformator / Strang liegt nicht vor."
        ),
        "disclaimer": "Keine automatische Addierung weiterer Anlagen im gleichen Netzsegment.",
    }


def build_scenario_next_step_note(project_id: int | None = None) -> dict[str, Any]:
    path = f"/projects/{project_id}/szenarien-vergleich" if project_id else None
    return {
        "message": (
            "Szenarienvergleich: Varianten (Leistung, Spannungsebene, Speicher) als separates "
            "Szenario speichern und gegenüberstellen."
        ),
        "link_path": path,
        "disclaimer": "MVP analysiert jeweils einen Eingabe-Snapshot; Vergleich über gespeicherte Szenarien.",
    }


def build_projektierer_perspective(
    eingabe: dict[str, Any],
    input_data: GridConnectionInput,
    *,
    project_id: int | None = None,
) -> dict[str, Any]:
    plant_ctx = resolve_plant_context(eingabe)
    from engine.berechnung import bestimme_spannungsebene

    u_kv = float(eingabe.get("nennspannung", 20))
    ebene = bestimme_spannungsebene(u_kv)

    return {
        "plant_type": plant_ctx.plant_type.value,
        "plant_type_label": plant_ctx.config.label,
        "dc_kwp": plant_ctx.dc_kwp,
        "ac_kw": plant_ctx.ac_kw,
        "overbuild_ratio": plant_ctx.overbuild_ratio,
        "screening_power_kw": plant_ctx.screening_power_kw,
        "cos_phi": plant_ctx.power_factor,
        "cos_phi_source": plant_ctx.power_factor_source,
        "power_factor": plant_ctx.power_factor,
        "power_factor_source": plant_ctx.power_factor_source,
        "simultaneity_factor": plant_ctx.simultaneity_factor,
        "simultaneity_note": plant_ctx.config.simultaneity_note,
        "reactive_power_mode": plant_ctx.reactive_power_mode,
        "feed_in_profile_note": plant_ctx.config.feed_in_profile_note,
        "feed_in_management_class": plant_ctx.feed_in_management_class,
        "process_timeline": build_process_timeline(
            input_data, projektreife=str(eingabe.get("projektreife") or "") or None
        ),
        "bkz_hint": build_bkz_hint(input_data, spannungsebene=ebene),
        "nvp_recommendation": build_nvp_recommendation(eingabe, input_data, plant_ctx=plant_ctx),
        "tab_disclaimer": build_tab_disclaimer(eingabe),
        "kumulation_warning": build_kumulation_warning(),
        "scenario_comparison_note": build_scenario_next_step_note(project_id),
        "reactive_power_threshold_kw": REACTIVE_POWER_SCREENING_KW,
        "disclaimer": (
            "Projektierer-Perspektive: strukturierte Vorplanung ohne Netzanschlusszusage "
            "und ohne freie Kapazitätsbehauptung."
        ),
    }
