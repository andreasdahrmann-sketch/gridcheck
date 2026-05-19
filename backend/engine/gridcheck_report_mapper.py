"""
Adapter: vollstaendiges Engine-Ergebnis (berechne_netzanschluss) ->
kanonisches GridcheckReportData-JSON (siehe frontend/lib/reports).

Hinweis: Einzelne Felder sind heuristisch aus der bestehenden Engine befuellt,
bis Asset-Kandidaten und detaillierte Risiko-Zerlegung im Backend verfuegbar sind.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from engine.berechnung import ENGINE_VERSION

StakeholderType = Literal["project_developer", "grid_operator", "investor"]
LegacyReportType = Literal["projektierer", "vnb", "invest"]

REPORT_TYPE_TO_STAKEHOLDER: dict[LegacyReportType, StakeholderType] = {
    "projektierer": "project_developer",
    "vnb": "grid_operator",
    "invest": "investor",
}

_FALLBACK_NEXT_STEPS = [
    "Netzanschlussanfrage beim zustaendigen VNB mit vollstaendigen technischen Unterlagen vorbereiten.",
    "Anschlussvariante und Leistungsfall grob gegenzeichnen (inkl. moeglicher Einspeisebegrenzung).",
    "Oeffentliche Datenlage und offene Annahmen im Projektteam explizit dokumentieren.",
]


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _map_technology(
    eingabe: dict[str, Any],
) -> Literal["pv", "wind", "battery", "hybrid", "load", "other"]:
    raw = _s(eingabe.get("anlagentyp"), "PV").lower()
    comps = (
        eingabe.get("project_components")
        if isinstance(eingabe.get("project_components"), list)
        else []
    )
    types = {
        str(c.get("component_type", "")).lower() for c in comps if isinstance(c, dict)
    }
    if len(types) > 1:
        return "hybrid"
    if "battery" in types:
        return "battery"
    if "wind" in types:
        return "wind"
    if raw in {"pv", "solar", "photovoltaik"}:
        return "pv"
    if raw in {"wind", "wt"}:
        return "wind"
    if raw in {"battery", "batterie", "speicher"}:
        return "battery"
    if raw in {"last", "load", "verbrauch"}:
        return "load"
    return "other"


def _map_operation_mode(
    anschlussart: str,
) -> Literal["feed_in", "consumption", "bidirectional", "mixed"]:
    a = _s(anschlussart, "Einspeisung")
    if a == "Einspeisung":
        return "feed_in"
    if a == "Entnahme":
        return "consumption"
    if a == "Speicher":
        return "bidirectional"
    return "mixed"


def _voltage_level_from_kv(u_kv: float) -> Literal["lv", "mv", "hv", "ehv", "unknown"]:
    if u_kv < 1:
        return "lv"
    if u_kv <= 35:
        return "mv"
    if u_kv <= 110:
        return "hv"
    if u_kv > 110:
        return "ehv"
    return "unknown"


def _de_risk_to_en(
    level: str | None,
) -> Literal["low", "medium", "high", "critical", "unknown"]:
    if not level:
        return "unknown"
    m = {
        "niedrig": "low",
        "mittel": "medium",
        "hoch": "high",
        "sehr_hoch": "critical",
    }
    return m.get(str(level).strip().lower(), "unknown")  # type: ignore[return-value]


def _overall_risk_from_fazit(
    fazit: dict[str, Any], scores: dict[str, Any]
) -> Literal["low", "medium", "high", "critical", "unknown"]:
    ents = _s(fazit.get("entscheidung"), "B")
    g = _f(scores.get("gesamt"), 50.0)
    if ents == "C" or g < 35:
        return "high"
    if ents == "B" or g < 60:
        return "medium"
    if ents == "A" and g >= 70:
        return "low"
    return "medium"


def _recommendation_from_fazit(
    fazit: dict[str, Any],
) -> Literal["go", "conditional_go", "review_required", "no_go"]:
    ents = _s(fazit.get("entscheidung"), "B")
    if ents == "A":
        return "go"
    if ents == "B":
        return "conditional_go"
    return "no_go"


def _n1_screening(n1: dict[str, Any]) -> dict[str, Any]:
    n1_klasse = _s(n1.get("n1_klasse"), "")
    sicher = bool(n1.get("n1_sicher"))
    bew = _s(n1.get("bewertung"), "")
    nachweise_fehlend = (
        n1.get("nachweise_fehlend")
        if isinstance(n1.get("nachweise_fehlend"), list)
        else []
    )
    detail_emps = (
        n1.get("detail_empfehlungen")
        if isinstance(n1.get("detail_empfehlungen"), list)
        else []
    )
    limitations: list[str] = [str(x) for x in nachweise_fehlend if str(x).strip()]
    for ann in (n1.get("detail_annahmen") or [])[:5]:
        if str(ann).strip():
            limitations.append(str(ann))
    if not limitations:
        limitations.append(
            "Oeffentliche/modellierte Datenbasis ohne vollstaendige Betriebsmittelparameter."
        )

    follow = [str(x) for x in detail_emps if str(x).strip()]
    if not follow:
        follow.append("Vertiefende netztechnische Pruefung mit VNB-Daten empfohlen.")

    if n1_klasse in ("N1-0", "N1-1"):
        status: Literal[
            "not_applicable",
            "screening_only",
            "limited",
            "critical",
            "requires_grid_operator_data",
        ] = "screening_only"
    elif n1_klasse in ("N1-2",):
        status = "limited"
    elif bew == "ROT" or not sicher:
        status = "critical"
    elif n1_klasse in ("N1-3", "N1-4") and not n1.get("dso_daten_vorhanden"):
        status = "requires_grid_operator_data"
    else:
        status = "limited"

    summary = _s(
        n1.get("detail_text") or n1.get("topologie_text"),
        "N-1-Screening auf Basis der Engine-Heuristik.",
    )

    return {
        "status": status,
        "score": int(_f(n1.get("n1_konfidenz"), 0)) or None,
        "summary": summary,
        "limitations": limitations[:12],
        "requiredFollowUp": follow[:12],
    }


def _cost_items_from_kosten(kosten: dict[str, Any]) -> list[dict[str, Any]]:
    low = int(_f(kosten.get("band_niedrig_eur"), 0))
    base = int(
        _f(kosten.get("band_basis_eur") or kosten.get("investition_gesamt_eur"), 0)
    )
    high = int(_f(kosten.get("band_hoch_eur"), 0))
    conf_pct = _f(kosten.get("konfidenz_prozent"), 50)
    conf: Literal["low", "medium", "high"] = (
        "high" if conf_pct >= 70 else "medium" if conf_pct >= 45 else "low"
    )
    items = [
        {
            "label": "Trasse / Kabel / Tiefbau",
            "low": max(0, int(_f(kosten.get("kosten_trasse_eur"), 0) * 0.85)),
            "base": int(_f(kosten.get("kosten_trasse_eur"), 0)),
            "high": int(_f(kosten.get("kosten_trasse_eur"), 0) * 1.15),
            "confidence": conf,
            "comment": "Anteil aus Kostenschätzung der Engine",
        },
        {
            "label": "Station / Schaltanlage",
            "low": max(0, int(_f(kosten.get("kosten_station_eur"), 0) * 0.85)),
            "base": int(_f(kosten.get("kosten_station_eur"), 0)),
            "high": int(_f(kosten.get("kosten_station_eur"), 0) * 1.2),
            "confidence": conf,
        },
        {
            "label": "Planung / Genehmigung",
            "low": max(
                0,
                int(
                    (
                        _f(kosten.get("kosten_planung_eur"), 0)
                        + _f(kosten.get("kosten_genehmigung_eur"), 0)
                    )
                    * 0.9
                ),
            ),
            "base": int(
                _f(kosten.get("kosten_planung_eur"), 0)
                + _f(kosten.get("kosten_genehmigung_eur"), 0)
            ),
            "high": int(
                (
                    _f(kosten.get("kosten_planung_eur"), 0)
                    + _f(kosten.get("kosten_genehmigung_eur"), 0)
                )
                * 1.15
            ),
            "confidence": conf,
        },
    ]
    if low <= 0 and base > 0:
        low = int(base * 0.85)
    if high <= 0 and base > 0:
        high = int(base * 1.15)
    return items


def _merge_grid_v2_into_assessment(
    payload: dict[str, Any], engine_result: dict[str, Any]
) -> None:
    """Enrich canonical report assessment from grid_calculation_v2 + projektierer_perspective."""
    v2 = engine_result.get("grid_calculation_v2")
    if not isinstance(v2, dict):
        return
    assessment = payload.get("assessment")
    if not isinstance(assessment, dict):
        return

    persp = v2.get("projektierer_perspective")
    if isinstance(persp, dict):
        plant = persp.get("plant_type_label") or persp.get("plant_type")
        if plant:
            line = f"Anlagentyp (Screening): {plant}"
            if persp.get("ac_kw") is not None:
                line += f", AC {_f(persp.get('ac_kw')):.0f} kW"
            if line not in assessment.get("keyFindings", []):
                assessment.setdefault("keyFindings", []).append(line)
        tl = persp.get("process_timeline") or {}
        if isinstance(tl, dict) and tl.get("estimated_total"):
            step = f"Zeitplan (heuristisch): {tl['estimated_total']}"
            if step not in assessment.get("nextSteps", []):
                assessment.setdefault("nextSteps", []).append(step)
        bkz = persp.get("bkz_hint") or {}
        if isinstance(bkz, dict) and bkz.get("hint"):
            hint = str(bkz["hint"])
            if hint not in assessment.get("assumptions", []):
                assessment.setdefault("assumptions", []).append(hint)

    feasibility = v2.get("feasibility")
    if isinstance(feasibility, dict):
        status = feasibility.get("status")
        summary = feasibility.get("summary")
        if summary and summary not in assessment.get("keyFindings", []):
            assessment.setdefault("keyFindings", []).append(str(summary))
        elif status:
            assessment.setdefault("keyFindings", []).append(f"grid_calculation_v2: {status}")

    eeg = v2.get("eeg_feed_in_screening")
    if isinstance(eeg, dict) and eeg.get("applicable"):
        for hint in (eeg.get("hints") or [])[:3]:
            text = f"EEG: {hint}"
            if text not in assessment.get("warnings", []):
                assessment.setdefault("warnings", []).append(text)


def _sources_from_engine(
    engine_result: dict[str, Any],
    *,
    retrieved_at: str,
) -> list[dict[str, Any]]:
    dq = (
        engine_result.get("datenqualitaet")
        if isinstance(engine_result.get("datenqualitaet"), dict)
        else {}
    )
    sources: list[dict[str, Any]] = [
        {
            "sourceId": "engine",
            "sourceName": "GridCheck Rechenkern",
            "sourceType": "model_assumption",
            "retrievedAt": retrieved_at,
            "version": _s(engine_result.get("engine_version"), ENGINE_VERSION),
            "confidence": "high",
            "usedFor": ["scores", "n1_screening", "thermal_voltage"],
        },
        {
            "sourceId": "user_input",
            "sourceName": "Projekteingaben",
            "sourceType": "user_input",
            "retrievedAt": retrieved_at,
            "confidence": "high",
            "usedFor": ["project", "location", "grid_assumptions"],
        },
    ]
    dq_klasse = _s(dq.get("klasse"), "C")
    sources.append(
        {
            "sourceId": "data_quality",
            "sourceName": f"Datenqualitaet ({dq_klasse})",
            "sourceType": "model_assumption",
            "retrievedAt": retrieved_at,
            "confidence": "medium",
            "usedFor": ["confidence", "warnings"],
        }
    )
    return sources


def _grid_pressure_indicators(engine_result: dict[str, Any]) -> list[dict[str, Any]]:
    eingabe = (
        engine_result.get("eingabe")
        if isinstance(engine_result.get("eingabe"), dict)
        else {}
    )
    bestehend = _f(eingabe.get("bestehende_einspeisung_mw"), 0.0)
    route = (
        engine_result.get("route_environment")
        if isinstance(engine_result.get("route_environment"), dict)
        else {}
    )
    out: list[dict[str, Any]] = []
    if bestehend > 0.1:
        out.append(
            {
                "indicatorId": "existing_feed_in",
                "label": "Bestehende Einspeisung im Modell",
                "level": "medium",
                "detail": f"Im Umfeld werden ca. {bestehend:.2f} MW bestehende Einspeisung beruecksichtigt.",
            }
        )
    rl = _s(route.get("risk_level"), "")
    if rl:
        out.append(
            {
                "indicatorId": "route_environment",
                "label": "Trasse / Umwelt",
                "level": _de_risk_to_en(rl),
                "detail": _s(route.get("summary"), "Trassenrisiko aus Pre-Check."),
            }
        )
    if not out:
        out.append(
            {
                "indicatorId": "grid_pressure_placeholder",
                "label": "Netzdruck-Indikatoren",
                "level": "unknown",
                "detail": "Keine zusaetzlichen regionalen Indikatoren im aktuellen Engine-Output.",
            }
        )
    return out


def _connection_candidates(
    eingabe: dict[str, Any], u_kv: float
) -> list[dict[str, Any]]:
    dist = _f(eingabe.get("entfernung_km"), 1.0)
    vl = _voltage_level_from_kv(u_kv)
    return [
        {
            "candidateId": "model-1",
            "label": "Modell-Anschluss gemaess Eingabe (Leitung / Stationspfad)",
            "assetType": "line",
            "voltageLevel": vl,
            "distanceKm": round(dist, 3),
            "confidence": "medium",
            "technicalFitScore": 55,
            "costRisk": "medium",
            "routeRisk": "medium",
            "comment": "Vereinfachtes Ein-Kandidaten-Modell bis OSM-/Asset-Kandidaten angebunden sind.",
        }
    ]


def build_gridcheck_report_data_from_engine_result(
    engine_result: dict[str, Any],
    *,
    stakeholder_type: StakeholderType,
    project_id: str,
    project_name: str,
    report_id: str | None = None,
    audit_id: str | None = None,
    created_at: str | None = None,
    generated_by: Literal["system", "user", "admin"] = "system",
    generated_by_user_id: str | None = None,
    status: Literal["draft", "final", "archived"] = "draft",
    report_version: str = "0.1.0",
    scoring_version: str = "scores-v1",
) -> dict[str, Any]:
    """
    Erzeugt das kanonische Report-JSON. Erwartet status==OK Engine-Dict (inkl. eingabe, fazit, n1, kosten, revision).
    """
    if engine_result.get("status") != "OK":
        raise ValueError("engine_result.status muss OK sein")

    eingabe = (
        engine_result.get("eingabe")
        if isinstance(engine_result.get("eingabe"), dict)
        else {}
    )
    fazit = (
        engine_result.get("fazit")
        if isinstance(engine_result.get("fazit"), dict)
        else {}
    )
    n1 = engine_result.get("n1") if isinstance(engine_result.get("n1"), dict) else {}
    kosten = (
        engine_result.get("kosten")
        if isinstance(engine_result.get("kosten"), dict)
        else {}
    )
    scores = (
        engine_result.get("scores")
        if isinstance(engine_result.get("scores"), dict)
        else {}
    )
    warnungen = (
        engine_result.get("warnungen")
        if isinstance(engine_result.get("warnungen"), list)
        else []
    )
    empfehlungen = (
        engine_result.get("empfehlungen")
        if isinstance(engine_result.get("empfehlungen"), list)
        else []
    )
    transparenz = (
        engine_result.get("transparenz")
        if isinstance(engine_result.get("transparenz"), dict)
        else {}
    )
    revision = (
        engine_result.get("revision")
        if isinstance(engine_result.get("revision"), dict)
        else {}
    )
    projektprofil = (
        engine_result.get("projektprofil")
        if isinstance(engine_result.get("projektprofil"), dict)
        else {}
    )
    route_environment = (
        engine_result.get("route_environment")
        if isinstance(engine_result.get("route_environment"), dict)
        else {}
    )
    stakeholder_bw = (
        engine_result.get("stakeholder_bewertung")
        if isinstance(engine_result.get("stakeholder_bewertung"), dict)
        else {}
    )
    prov = (
        engine_result.get("_provenance")
        if isinstance(engine_result.get("_provenance"), dict)
        else {}
    )

    u_kv = _f(eingabe.get("nennspannung"), 20.0)
    p_mw = _f(eingabe.get("leistung_mw"), 0.0)
    max_export_kw = _f(projektprofil.get("max_export_kw"), p_mw * 1000.0)
    max_import_kw = _f(projektprofil.get("max_import_kw"), 0.0)
    op_mode = _map_operation_mode(_s(eingabe.get("anschlussart"), "Einspeisung"))
    feed_mw = round(max_export_kw / 1000.0, 4) if max_export_kw else round(p_mw, 4)
    cons_mw_val = round(max_import_kw / 1000.0, 4) if max_import_kw else None
    if op_mode == "feed_in":
        feed_in_capacity: float | None = feed_mw
        consumption_capacity: float | None = None
    elif op_mode == "consumption":
        feed_in_capacity = None
        consumption_capacity = (
            cons_mw_val if cons_mw_val and cons_mw_val > 0 else round(p_mw, 4)
        )
    else:
        feed_in_capacity = feed_mw
        consumption_capacity = cons_mw_val if cons_mw_val and cons_mw_val > 0 else None

    loc = (
        eingabe.get("project_location")
        if isinstance(eingabe.get("project_location"), dict)
        else {}
    )
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    if lat is None or lon is None:
        lat = 51.1657
        lon = 10.4515
        warn_extra = "Standortkoordinaten nicht gesetzt - Platzhalterkoordinate (DE-Mitte) nur fuer Schema-Vollstaendigkeit."
        if isinstance(warnungen, list) and warn_extra not in warnungen:
            warnungen = [*warnungen, warn_extra]
    lat_f = _f(lat, 51.1657)
    lon_f = _f(lon, 10.4515)

    now = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rid = report_id or str(uuid.uuid4())
    aid = audit_id or _s(revision.get("hash")) or str(uuid.uuid4())

    assumptions = [
        str(x) for x in (transparenz.get("assumptions") or []) if str(x).strip()
    ]
    warnings = [str(x) for x in warnungen if str(x).strip()]
    disclaimers_t = [
        str(x) for x in (transparenz.get("disclaimers") or []) if str(x).strip()
    ]

    next_steps = [str(x) for x in empfehlungen if str(x).strip()]
    for pad in _FALLBACK_NEXT_STEPS:
        if len(next_steps) >= 5:
            break
        if pad not in next_steps:
            next_steps.append(pad)

    key_findings = [
        _s(fazit.get("text")),
        _s(fazit.get("detail")),
        _s(projektprofil.get("summary")),
        _s(route_environment.get("summary")),
    ]
    key_findings = [k for k in key_findings if k][:8]
    if not key_findings:
        for candidate in empfehlungen:
            text = str(candidate).strip()
            if text:
                key_findings = [text]
                break
    if not key_findings:
        key_findings = [
            "Vorläufige technische Einschätzung auf Basis der Engine-Berechnung."
        ]

    summary = " ".join(
        x
        for x in [
            _s(fazit.get("text")),
            _s(fazit.get("detail")),
        ]
        if x
    )
    if not summary:
        summary = "Vorläufige technische Einschätzung auf Basis der Engine-Berechnung."

    main_cost_drivers = [
        str(x) for x in (kosten.get("hauptrisikotreiber") or []) if str(x).strip()
    ]
    if not main_cost_drivers:
        main_cost_drivers = [
            "Trasse/Entfernung",
            "Spannungsebene/Stationssope",
            "Datenqualitaet",
        ]

    cost_items = _cost_items_from_kosten(kosten)
    low_e = int(_f(kosten.get("band_niedrig_eur"), 0))
    base_e = int(
        _f(kosten.get("band_basis_eur") or kosten.get("investition_gesamt_eur"), 0)
    )
    high_e = int(_f(kosten.get("band_hoch_eur"), 0))
    if base_e <= 0:
        base_e = max(low_e, high_e, 1)

    overall = _overall_risk_from_fazit(fazit, scores)
    grid_r = overall
    route_r = _de_risk_to_en(route_environment.get("risk_level"))
    cost_r = (
        "high"
        if high_e > base_e * 1.35
        else "medium"
        if high_e > base_e * 1.15
        else "low"
    )
    timeline_r = "medium"
    dq_block = (
        engine_result.get("datenqualitaet")
        if isinstance(engine_result.get("datenqualitaet"), dict)
        else {}
    )
    dq_class = _s(dq_block.get("klasse"), "C")
    if dq_class in ("D", "C"):
        data_q: Literal["low", "medium", "high", "critical", "unknown"] = "high"
    elif dq_class == "B":
        data_q = "medium"
    elif dq_class == "A":
        data_q = "low"
    else:
        data_q = "unknown"

    tech = _map_technology(eingabe)
    curtail_r: Literal["low", "medium", "high", "critical", "unknown"] | None = None
    if tech in ("pv", "wind", "battery", "hybrid"):
        curtail_r = "medium" if route_r in ("medium", "high", "critical") else "low"

    input_hash = (
        _s(prov.get("request_checksum"))
        or _s(revision.get("previous_hash"))
        or "pending-input-hash"
    )
    result_hash = (
        _s(prov.get("result_checksum"))
        or _s(revision.get("hash"))
        or "pending-result-hash"
    )

    payload: dict[str, Any] = {
        "report": {
            "reportId": rid,
            "auditId": aid,
            "reportVersion": report_version,
            "modelVersion": _s(engine_result.get("engine_version"), ENGINE_VERSION),
            "scoringVersion": scoring_version,
            "createdAt": now,
            "stakeholderType": stakeholder_type,
            "status": status,
        },
        "project": {
            "projectId": project_id,
            "projectName": project_name,
            "technology": tech,
            "installedCapacityMw": round(
                _f(projektprofil.get("total_installed_kw"), p_mw * 1000) / 1000.0, 4
            ),
            "feedInCapacityMw": feed_in_capacity,
            "consumptionCapacityMw": consumption_capacity,
            "storagePowerMw": None,
            "storageCapacityMwh": None,
            "operationMode": op_mode,
            "targetCod": eingabe.get("foerderfrist")
            if isinstance(eingabe.get("foerderfrist"), str)
            else None,
        },
        "location": {
            "addressLabel": _s(
                loc.get("address_hint") or eingabe.get("standort") or eingabe.get("ort")
            ),
            "municipality": _s(eingabe.get("ort")),
            "federalState": None,
            "latitude": lat_f,
            "longitude": lon_f,
            "parcelInfo": None,
            "gridOperatorArea": eingabe.get("vnb_gebiet")
            if isinstance(eingabe.get("vnb_gebiet"), str)
            else None,
        },
        "grid": {
            "recommendedVoltageLevel": _voltage_level_from_kv(u_kv),
            "recommendedConnectionType": _s(eingabe.get("anschlussart"), "Einspeisung"),
            "candidateConnectionPoints": _connection_candidates(eingabe, u_kv),
            "n1Screening": _n1_screening(n1),
            "gridPressureIndicators": _grid_pressure_indicators(engine_result),
        },
        "risks": {
            "overallRisk": overall,
            "gridConnectionRisk": grid_r,
            "routeRisk": route_r,
            "costRisk": cost_r,
            "timelineRisk": timeline_r,
            "permittingRisk": "unknown",
            "curtailmentRisk": curtail_r,
            "dataQualityRisk": data_q,
        },
        "cost": {
            "currency": "EUR",
            "lowEstimate": low_e,
            "baseEstimate": base_e,
            "highEstimate": high_e,
            "costItems": cost_items,
            "mainCostDrivers": main_cost_drivers[:8],
            "confidence": "medium",
        },
        "assessment": {
            "recommendation": _recommendation_from_fazit(fazit),
            "summary": summary[:4000],
            "keyFindings": key_findings,
            "assumptions": assumptions[:20]
            if assumptions
            else ["Siehe Transparenzblock der Engine."],
            "warnings": warnings[:30]
            if warnings
            else [
                "Keine zusaetzlichen Warnungen aus der Engine — trotzdem nur vorlaeufige Einordnung."
            ],
            "nextSteps": next_steps[:15],
        },
        "sources": _sources_from_engine(engine_result, retrieved_at=now),
        "audit": {
            "inputHash": input_hash,
            "resultHash": result_hash,
            "generatedBy": generated_by,
            "generatedByUserId": generated_by_user_id,
            "immutable": False,
        },
    }

    if disclaimers_t:
        payload["assessment"]["warnings"] = list(
            dict.fromkeys(payload["assessment"]["warnings"] + disclaimers_t[:3])
        )

    if stakeholder_bw.get("konflikt_summary"):
        payload["assessment"]["keyFindings"].append(
            _s(stakeholder_bw.get("konflikt_summary"))
        )

    _merge_grid_v2_into_assessment(payload, engine_result)

    return payload


def stakeholder_type_for_legacy_report_type(report_type: str) -> StakeholderType:
    key = str(report_type).strip().lower()
    if key not in REPORT_TYPE_TO_STAKEHOLDER:
        raise ValueError(f"Unbekannter report_type: {report_type}")
    return REPORT_TYPE_TO_STAKEHOLDER[key]  # type: ignore[index]
