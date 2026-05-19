"""
Grid connection screening v2 — transparente Plausibilitaetsbewertung mit dokumentierten Annahmen.

Keine verbindliche Netzanschlusszusage. Keine Schein-N-1-Lastflussberechnung ohne Topologiedaten.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from engine.cable_database import get_cable_params, get_cable_resistance_at_temp
from engine.cable_length import estimate_cable_length_from_location
from engine.grid_calculation_types import (
    AppliedThresholds,
    CalculationAssumption,
    Coordinates,
    FeasibilityResult,
    GridCalculationResult,
    GridConnectionInput,
    N1Assessment,
    NextStep,
    ShortCircuitResult,
    ThermalResult,
    VoltageDropInputs,
    VoltageDropResult,
)
from engine.nb_akzeptanz_screening import (
    assess_transformer_loading,
    build_norm_references_applied,
    grid_form_note,
    merge_screening_into_feasibility,
    screen_coincidence_factor,
    screen_eeg_feed_in,
    screen_network_feedback,
    screen_protection_concept,
    screen_reactive_power,
)
from engine.plant_types import resolve_plant_context
from engine.projektierer_output import build_projektierer_perspective

CALCULATION_VERSION = "2.3.0"

THRESHOLDS = {
    "voltage_drop": {
        "low_voltage_percent": 3.0,
        "medium_voltage_percent": 2.0,
        "norm": "EN 50160:2010, VDE-AR-N 4100:2019 (TAB)",
    },
    "power": {
        "ns_generation_max_kw": 100.0,
        "ns_consumption_standard_kw": 100.0,
        "ms_direct_connection_kw": 100.0,
        "norm": "VDE-AR-N 4100:2019, BDEW Technische Richtlinien",
    },
}

N1_DISCLAIMER = (
    "HINWEIS: Eine normgerechte N-1-Analyse nach VDE-AR-N 4110 / ENTSO-E erfordert "
    "vollstaendige Netzmodelldaten und kann ohne diese nicht durchgefuehrt werden. "
    "Diese Ausgabe ist eine qualitative N-1-Bewertung (Assessment), keine Lastflussanalyse."
)

SHORT_CIRCUIT_CANNOT_CALCULATE_DISCLAIMER = (
    "Eine normgerechte Kurzschlussberechnung nach IEC 60909 ist ohne "
    "Netzdaten des Betreibers nicht moeglich. Die Kurzschlussberechnung "
    "muss durch den Netzbetreiber oder auf Basis offizieller Netzdaten erfolgen."
)


def _voltage_level_from_kv(u_kv: float) -> str:
    from engine.berechnung import bestimme_spannungsebene

    ebene = bestimme_spannungsebene(u_kv)
    if ebene == "NS":
        return "low"
    if ebene == "HS":
        return "high"
    return "medium"


def _nominal_kv(voltage_level: str) -> float:
    if voltage_level == "low":
        return 0.4
    if voltage_level == "high":
        return 110.0
    return 20.0


def _infer_cable_type(eingabe: dict[str, Any], leitungstyp: str) -> str:
    explicit = str(eingabe.get("leitungsart") or eingabe.get("cable_type") or "").strip().lower()
    if explicit in ("freileitung", "overhead", "ol"):
        return "overhead"
    if explicit in ("kabel", "underground", "cs", "erdverlegt"):
        return "underground"
    lt = leitungstyp.upper()
    if any(x in lt for x in ("NAYY", "NAY", "FREI", "OVERHEAD")):
        return "overhead"
    return "underground"


def _map_topology(topologie: str | None) -> str:
    mapping = {
        "stich": "radial",
        "stich_mit_notverbindung": "radial",
        "ring": "ring",
        "ring_offen": "ring",
        "ring_geschlossen": "ring",
        "doppelstich": "radial",
        "vermascht": "meshed",
    }
    return mapping.get(str(topologie or "").strip().lower(), "unknown")


def _effective_screening_kw(input_data: GridConnectionInput) -> float:
    return input_data.screening_power_kw or input_data.power_kw


def grid_connection_input_from_engine(eingabe: dict[str, Any]) -> GridConnectionInput:
    """Map legacy engine eingabe dict to GridConnectionInput v2."""
    u_kv = float(eingabe.get("nennspannung", 20))
    voltage_level = _voltage_level_from_kv(u_kv)
    plant_ctx = resolve_plant_context(eingabe, voltage_level=voltage_level)  # type: ignore[arg-type]
    ac_kw = plant_ctx.ac_kw

    project_type = plant_ctx.config.project_type
    components = eingabe.get("project_components") or []
    if isinstance(components, list) and len(components) > 1 and project_type != "mixed":
        project_type = "mixed"

    leitungstyp = str(eingabe.get("leitungstyp", "NA2XS2Y150"))
    from engine.berechnung import LEITUNGSDATEN

    lt_meta = LEITUNGSDATEN.get(leitungstyp, {})
    material_raw = str(lt_meta.get("material", "Al"))
    cable_material = "copper" if material_raw in ("Cu",) else "aluminum"
    cross_section = float(lt_meta.get("querschnitt", 150))

    entfernung = float(eingabe.get("entfernung_km", 1.0))
    cable_source: str = "user_input"
    loc = eingabe.get("project_location")
    if isinstance(loc, dict) and loc.get("latitude") is not None and loc.get("longitude") is not None:
        cable_source = "estimated"
    if eingabe.get("entfernung_heuristisch"):
        cable_source = "estimated"

    coords = None
    if isinstance(loc, dict):
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if lat is not None and lng is not None:
            coords = Coordinates(lat=float(lat), lng=float(lng))

    sk = eingabe.get("sk_mva")
    trafo_s = eingabe.get("trafo_s_mva")
    trafo_uk = eingabe.get("trafo_uk_prozent", eingabe.get("uk_prozent"))
    trafo_load = eingabe.get(
        "transformer_load_percent",
        eingabe.get("bestand_trafo_auslastung", eingabe.get("bestand_auslastung_prozent")),
    )

    cos_known = eingabe.get("cos_phi_known")
    if cos_known is None:
        cos_known = plant_ctx.power_factor_source == "nutzer"

    topo = _map_topology(eingabe.get("topologie"))

    return GridConnectionInput(
        project_type=project_type,  # type: ignore[arg-type]
        plant_type=plant_ctx.plant_type.value,  # type: ignore[arg-type]
        power_kw=ac_kw,
        screening_power_kw=plant_ctx.screening_power_kw,
        dc_kwp=plant_ctx.dc_kwp,
        ac_kw=ac_kw,
        simultaneity_factor=plant_ctx.simultaneity_factor,
        reactive_power_mode=plant_ctx.reactive_power_mode,
        power_factor=plant_ctx.power_factor,
        voltage_level=voltage_level,  # type: ignore[arg-type]
        connection_type="three_phase",
        cos_phi_known=bool(cos_known) if cos_known is not None else None,
        existing_connection=bool(eingabe.get("existing_connection"))
        if eingabe.get("existing_connection") is not None
        else None,
        network_form=topo,  # type: ignore[arg-type]
        cable_length_km=entfernung,
        cable_length_source=cable_source,  # type: ignore[arg-type]
        cable_cross_section_mm2=cross_section,
        cable_material=cable_material,  # type: ignore[arg-type]
        cable_type=_infer_cable_type(eingabe, leitungstyp),  # type: ignore[arg-type]
        transformer_power_kva=float(trafo_s) * 1000.0 if trafo_s else None,
        transformer_load_percent=float(trafo_load) if trafo_load is not None else None,
        transformer_impedance_percent=float(trafo_uk) if trafo_uk else None,
        network_short_circuit_mva=float(sk) if sk else None,
        grid_topology=topo,  # type: ignore[arg-type]
        coordinates=coords,
        network_operator=eingabe.get("netzbetreiber"),
    )


def calculate_voltage_drop(
    input_data: GridConnectionInput,
    assumptions: list[CalculationAssumption],
) -> VoltageDropResult:
    u_n_kv = _nominal_kv(input_data.voltage_level)
    u_n_v = u_n_kv * 1000.0
    cos_phi = input_data.power_factor
    sin_phi = math.sqrt(max(0.0, 1.0 - cos_phi * cos_phi))
    p_kw = _effective_screening_kw(input_data)

    if input_data.connection_type == "three_phase":
        current_a = (p_kw * 1000.0) / (math.sqrt(3) * u_n_v * cos_phi)
        formula = "ΔU = √3 × I × L × (R·cosφ + X·sinφ) [DIN EN 50480, 3-phasig]"
    else:
        current_a = (p_kw * 1000.0) / (u_n_v * cos_phi)
        formula = "ΔU = 2 × I × L × (R·cosφ + X·sinφ) [DIN EN 50480, 1-phasig]"

    vl_cable: str = "low" if input_data.voltage_level == "low" else "medium"
    cable_params = get_cable_params(
        input_data.cable_material,
        int(input_data.cable_cross_section_mm2),
        vl_cable,  # type: ignore[arg-type]
    )

    if cable_params:
        op_temp = 70 if input_data.voltage_level == "low" else 90
        r_per_km = get_cable_resistance_at_temp(
            cable_params["resistance_20"],
            input_data.cable_material,
            op_temp,
        )
        x_per_km = cable_params["reactance"]
    else:
        r_per_km = 0.387 if input_data.cable_material == "copper" else 0.641
        x_per_km = 0.069 if input_data.voltage_level == "low" else 0.109
        assumptions.append(
            CalculationAssumption(
                parameter="Kabelwiderstand & -reaktanz",
                assumed_value=f"R={r_per_km} Ohm/km, X={x_per_km} Ohm/km",
                reason=(
                    f"Kein exakter Eintrag fuer {input_data.cable_cross_section_mm2} mm² — "
                    "Standardwert 50 mm² verwendet"
                ),
                norm_reference="VDE 0276-603",
                confidence="medium",
            )
        )

    r_total = r_per_km * input_data.cable_length_km
    x_total = x_per_km * input_data.cable_length_km

    if input_data.connection_type == "three_phase":
        delta_u_v = math.sqrt(3) * current_a * (r_total * cos_phi + x_total * sin_phi)
    else:
        delta_u_v = 2 * current_a * (r_total * cos_phi + x_total * sin_phi)

    delta_u_percent = (delta_u_v / u_n_v) * 100.0
    limit = (
        THRESHOLDS["voltage_drop"]["low_voltage_percent"]
        if input_data.voltage_level == "low"
        else THRESHOLDS["voltage_drop"]["medium_voltage_percent"]
    )

    return VoltageDropResult(
        delta_u_percent=round(delta_u_percent, 2),
        delta_u_volt=round(delta_u_v, 2),
        limit_percent=limit,
        norm_reference=THRESHOLDS["voltage_drop"]["norm"],
        formula=formula,
        inputs=VoltageDropInputs(
            current_a=round(current_a, 1),
            length_km=input_data.cable_length_km,
            resistance_ohm_per_km=round(r_per_km, 4),
            reactance_ohm_per_km=round(x_per_km, 4),
            cos_phi=round(cos_phi, 4),
            sin_phi=round(sin_phi, 3),
            voltage_kv=u_n_kv,
        ),
        compliant=delta_u_percent <= limit,
        margin_percent=round(limit - delta_u_percent, 2),
    )


def calculate_short_circuit(
    input_data: GridConnectionInput,
    assumptions: list[CalculationAssumption],
) -> ShortCircuitResult:
    missing: list[str] = []
    if not input_data.network_short_circuit_mva and not input_data.transformer_power_kva:
        missing.append('Netz-Kurzschlussleistung S"k (MVA) am Einspeisepunkt')
        missing.append("Transformatordaten (Nennleistung kVA, Kurzschlussspannung uk%)")

    if missing:
        return ShortCircuitResult(
            calculation_method="estimated",
            cannot_calculate=True,
            missing_data=missing,
            data_quality="estimated",
            disclaimer=SHORT_CIRCUIT_CANNOT_CALCULATE_DISCLAIMER,
        )

    u_n_kv = _nominal_kv(input_data.voltage_level)
    c = 1.1
    uk = (input_data.transformer_impedance_percent or 6.0) / 100.0
    s_t_mva = (input_data.transformer_power_kva or 630.0) / 1000.0
    z_t = (uk * u_n_kv * u_n_kv) / s_t_mva

    vl_cable: str = "low" if input_data.voltage_level == "low" else "medium"
    cable_params = get_cable_params(
        input_data.cable_material,
        int(input_data.cable_cross_section_mm2),
        vl_cable,  # type: ignore[arg-type]
    )
    r_cable = (cable_params["resistance_20"] if cable_params else 0.387) * input_data.cable_length_km
    x_cable = (cable_params["reactance"] if cable_params else 0.069) * input_data.cable_length_km

    z_netz = 0.0
    if input_data.network_short_circuit_mva:
        z_netz = (u_n_kv * u_n_kv) / input_data.network_short_circuit_mva

    z_total = math.sqrt((z_netz * 0.1 + z_t * 0.2 + r_cable) ** 2 + (z_t * 0.98 + x_cable) ** 2)
    ik_max_ka = (c * u_n_kv) / (math.sqrt(3) * z_total) if z_total > 0 else 0.0

    assumptions.append(
        CalculationAssumption(
            parameter="Kurzschluss-Berechnung",
            assumed_value=f"Vereinfachte IEC 60909, Z_T={z_t:.3f} Ohm, uk={uk * 100:.1f}%",
            reason="Vollstaendige Netzimpedanz nicht verfuegbar — konservative Schaetzung",
            norm_reference="IEC 60909-0:2016",
            confidence="medium",
        )
    )

    return ShortCircuitResult(
        calculation_method="iec60909_simplified",
        ik_max_ka=round(ik_max_ka, 2),
        cannot_calculate=False,
        missing_data=[],
        data_quality="calculated",
        disclaimer=(
            "Vereinfachte Berechnung nach IEC 60909. Fuer die offizielle Netzanschlusspruefung "
            "ist eine vollstaendige Berechnung mit Netzbetreiberdaten erforderlich."
        ),
    )


def assess_n1(input_data: GridConnectionInput) -> N1Assessment:
    topology = input_data.grid_topology
    if topology == "unknown":
        return N1Assessment(
            assessment_type="insufficient_data",
            grid_topology="unknown",
            redundancy_available=None,
            critical_elements=[],
            recommendation=(
                "Netztopologie unbekannt. Fuer eine N-1-Beurteilung muessen vom Netzbetreiber "
                "Informationen zur Ringstruktur und verfuegbaren Reservekapazitaeten eingeholt werden."
            ),
            disclaimer=N1_DISCLAIMER,
            requires_detailed_study=True,
        )

    is_radial = topology == "radial"
    critical: list[str] = []
    if is_radial:
        critical.append("Einspeisekabel (keine Redundanz bei Strahlnetz)")
        critical.append("Ortsnetztransformator (falls nur einer vorhanden)")

    return N1Assessment(
        assessment_type="statistical_assessment",
        grid_topology=topology,  # type: ignore[arg-type]
        redundancy_available=topology in ("ring", "meshed"),
        critical_elements=critical,
        recommendation=(
            "Strahlnetz erkannt: Bei Ausfall des Einspeisekabels oder Transformators ist keine "
            "Versorgung moeglich. Fuer sensible Verbraucher oder grosse Erzeugungsanlagen "
            "Ringnetzanschluss oder zweite Einspeisung pruefen."
            if is_radial
            else "Ringnetz/Vermaschtes Netz: Grundsaetzliche Redundanz vorhanden. "
            "Belastung der Reserveinfrastruktur durch Netzbetreiber pruefen lassen."
        ),
        disclaimer=N1_DISCLAIMER,
        requires_detailed_study=is_radial or _effective_screening_kw(input_data) > 500,
    )


def calculate_thermal_load(
    input_data: GridConnectionInput,
    voltage_drop: VoltageDropResult,
    assumptions: list[CalculationAssumption],
) -> ThermalResult:
    vl_cable: str = "low" if input_data.voltage_level == "low" else "medium"
    cable_params = get_cable_params(
        input_data.cable_material,
        int(input_data.cable_cross_section_mm2),
        vl_cable,  # type: ignore[arg-type]
    )
    if not cable_params:
        assumptions.append(
            CalculationAssumption(
                parameter="Thermische Grenzbelastung",
                assumed_value="Standardwert 50 mm² Al verwendet",
                reason="Kein exakter Kabeleintrag gefunden",
                confidence="low",
            )
        )

    thermal_limit = float(cable_params["thermal_limit_a"] if cable_params else 160)
    utilization = (voltage_drop.inputs.current_a / thermal_limit) * 100.0 if thermal_limit > 0 else 999.0
    mat_label = "Cu" if input_data.cable_material == "copper" else "Al"

    return ThermalResult(
        current_a=voltage_drop.inputs.current_a,
        thermal_limit_a=thermal_limit,
        utilization_percent=round(utilization, 1),
        compliant=utilization <= 100.0,
        cable_type=f"{mat_label} {int(input_data.cable_cross_section_mm2)} mm²",
    )


def get_applied_thresholds(input_data: GridConnectionInput) -> AppliedThresholds:
    if input_data.project_type == "generation":
        power_limit = THRESHOLDS["power"]["ns_generation_max_kw"]
        basis = "VDE-AR-N 4100:2019 (TAB), Abschnitt 5 - Erzeugungsanlagen"
    elif input_data.project_type == "consumption":
        power_limit = THRESHOLDS["power"]["ns_consumption_standard_kw"]
        basis = "VDE-AR-N 4100:2019 (TAB), Abschnitt 4 - Verbrauch"
    else:
        power_limit = THRESHOLDS["power"]["ns_generation_max_kw"]
        basis = "VDE-AR-N 4100:2019 (TAB) - konservativster Wert angewendet"

    du_limit = (
        THRESHOLDS["voltage_drop"]["low_voltage_percent"]
        if input_data.voltage_level == "low"
        else THRESHOLDS["voltage_drop"]["medium_voltage_percent"]
    )

    return AppliedThresholds(
        voltage_drop_limit_percent=du_limit,
        voltage_drop_norm=THRESHOLDS["voltage_drop"]["norm"],
        power_limit_kw=power_limit,
        power_limit_basis=basis,
        connection_voltage_threshold_kw=THRESHOLDS["power"]["ms_direct_connection_kw"],
    )


def evaluate_feasibility(
    input_data: GridConnectionInput,
    voltage_drop: VoltageDropResult,
    short_circuit: ShortCircuitResult,
    n1: N1Assessment,
    thermal: ThermalResult,
    thresholds: AppliedThresholds,
) -> FeasibilityResult:
    conditions: list[str] = []
    required_documents: list[str] = []
    next_steps: list[NextStep] = []

    if not voltage_drop.compliant:
        conditions.append(
            f"Spannungsfall {voltage_drop.delta_u_percent:.2f}% ueberschreitet "
            f"Grenzwert {voltage_drop.limit_percent}% ({voltage_drop.norm_reference}). "
            "Kabelquerschnitt erhoehen oder Leitungslaenge reduzieren."
        )
        next_steps.append(
            NextStep(
                priority="immediate",
                action=(
                    f"Kabelquerschnitt pruefen: mindestens "
                    f"{math.ceil(input_data.cable_cross_section_mm2 * 1.5 / 10) * 10} mm² erwägen"
                ),
                responsible="planner",
                norm_reference="DIN EN 50480",
            )
        )

    if not thermal.compliant:
        conditions.append(
            f"Thermische Ueberlastung: {thermal.utilization_percent}% Auslastung "
            "uebersteigt 100% der Nennbelastbarkeit des Kabels."
        )

    screening_kw = _effective_screening_kw(input_data)
    if screening_kw > thresholds.power_limit_kw and input_data.voltage_level == "low":
        conditions.append(
            f"Screening-Leistung {screening_kw:.0f} kW (AC {input_data.power_kw:.0f} kW, "
            f"Gleichzeitigkeit beruecksichtigt) ueberschreitet typischen NS-Grenzwert "
            f"{thresholds.power_limit_kw:.0f} kW. MS-Direktanschluss (20 kV) pruefen. "
            f"({thresholds.power_limit_basis})"
        )
        next_steps.append(
            NextStep(
                priority="required",
                action="Klaerung der Anschlussebene (NS vs. MS) mit Netzbetreiber",
                responsible="network_operator",
                norm_reference="VDE-AR-N 4100:2019",
            )
        )

    if n1.requires_detailed_study:
        required_documents.append("N-1-Lastflussberechnung durch Netzbetreiber")
        next_steps.append(
            NextStep(
                priority="required",
                action="Systemstudie / N-1-Untersuchung beim Netzbetreiber beauftragen",
                responsible="network_operator",
            )
        )

    if short_circuit.cannot_calculate:
        required_documents.append("Kurzschlussberechnung nach IEC 60909 durch Netzbetreiber")

    required_documents.extend(
        [
            "Technische Anschlussbedingungen (TAB) des Netzbetreibers",
            "Netzanschlussbegehren mit Anlagedatenblatt",
            "Einstufung der Anlage nach VDE-AR-N 4105 (NS) oder 4110 (MS)",
        ]
    )
    required_documents = list(dict.fromkeys(required_documents))

    hard_fails = not voltage_drop.compliant or not thermal.compliant
    warnings = len(conditions) > 0
    data_quality_issues = input_data.cable_length_source != "user_input"

    if hard_fails:
        status = "likely_infeasible"
        confidence_level = "low" if data_quality_issues else "medium"
        confidence_reason = (
            "Berechnungsbasis teilweise geschaetzt — Vor-Ort-Pruefung erforderlich"
            if data_quality_issues
            else "Grenzwertverletzung auf Basis eingegebener Daten nachgewiesen"
        )
    elif warnings or n1.requires_detailed_study:
        status = "conditionally_feasible"
        confidence_level = "medium"
        confidence_reason = "Anschluss grundsaetzlich moeglich, Bedingungen muessen erfuellt werden"
    elif short_circuit.cannot_calculate:
        status = "requires_study"
        confidence_level = "medium"
        confidence_reason = "Fehlende Netzdaten — vollstaendige Bewertung nicht moeglich"
    else:
        status = "feasible"
        confidence_level = "medium" if data_quality_issues else "high"
        confidence_reason = "Alle geprueften Kriterien erfuellt"

    process_time = (
        "8-16 Wochen (MS-Anschluss, inkl. Systemstudie)"
        if screening_kw > 100
        else "4-8 Wochen (NS-Standardanschluss)"
    )

    return FeasibilityResult(
        status=status,  # type: ignore[arg-type]
        conditions=conditions,
        required_documents=required_documents,
        estimated_process_time=process_time,
        next_steps=next_steps,
        confidence_level=confidence_level,  # type: ignore[arg-type]
        confidence_reason=confidence_reason,
    )


def calculate_grid_connection(
    input_data: GridConnectionInput,
    *,
    anlagentyp: str | None = None,
) -> GridCalculationResult:
    assumptions: list[CalculationAssumption] = []

    assumptions.append(
        CalculationAssumption(
            parameter="Netzform / Leitungsführung",
            assumed_value=grid_form_note(input_data),
            reason="Topologie und Kabel/Freileitung beeinflussen R/X im Spannungsfall-Screening.",
            norm_reference="DIN EN 50480",
            confidence="medium" if input_data.grid_topology != "unknown" else "low",
        )
    )

    if input_data.cable_length_source != "user_input":
        assumptions.append(
            CalculationAssumption(
                parameter="Kabellaenge",
                assumed_value=f"{input_data.cable_length_km} km",
                reason=(
                    "Aus Luftlinie Standort → naechster Netzknoten berechnet (+ Trassenzuschlag)"
                    if input_data.cable_length_source == "geo_calculated"
                    else "Vom Benutzer geschaetzt oder heuristisch abgeleitet"
                ),
                confidence="medium" if input_data.cable_length_source == "geo_calculated" else "low",
            )
        )

    if input_data.plant_type:
        sim_note = ""
        if input_data.simultaneity_factor is not None:
            sim_note = f" (Gleichzeitigkeit {input_data.simultaneity_factor:.2f})"
        assumptions.append(
            CalculationAssumption(
                parameter="Anlagentyp / Gleichzeitigkeit",
                assumed_value=(
                    f"{input_data.plant_type}, AC={input_data.power_kw:.0f} kW, "
                    f"Screening={_effective_screening_kw(input_data):.0f} kW{sim_note}, "
                    f"cos φ={input_data.power_factor}"
                ),
                reason=(
                    "AC-Leistung am Netzanschluss; Screening-Leistung mit dokumentiertem "
                    "Gleichzeitigkeitsfaktor (Einzelprojekt, kein Cluster-Modell)."
                ),
                norm_reference="VNB-Planungsrichtlinien",
                confidence="medium",
            )
        )
    if input_data.dc_kwp and input_data.ac_kw:
        ratio = input_data.dc_kwp / input_data.ac_kw if input_data.ac_kw > 0 else None
        assumptions.append(
            CalculationAssumption(
                parameter="DC/AC-Verhaeltnis",
                assumed_value=f"DC {input_data.dc_kwp:.0f} kWp / AC {input_data.ac_kw:.0f} kW"
                + (f" ≈ {ratio:.2f}" if ratio else ""),
                reason="Ueberdimensionierung nur fuer Erzeugungsnachweis — Netzanschluss basiert auf AC.",
                norm_reference="VDE-AR-N 4105",
                confidence="high" if ratio else "medium",
            )
        )

    voltage_drop = calculate_voltage_drop(input_data, assumptions)
    short_circuit = calculate_short_circuit(input_data, assumptions)
    n1 = assess_n1(input_data)
    thermal = calculate_thermal_load(input_data, voltage_drop, assumptions)
    thresholds = get_applied_thresholds(input_data)
    feasibility = evaluate_feasibility(
        input_data, voltage_drop, short_circuit, n1, thermal, thresholds
    )

    transformer_assessment = assess_transformer_loading(input_data, assumptions)
    protection = screen_protection_concept(input_data)
    network_feedback = screen_network_feedback(input_data, anlagentyp=anlagentyp)
    coincidence = screen_coincidence_factor(input_data, assumptions)
    norm_refs = build_norm_references_applied(input_data)
    eeg = screen_eeg_feed_in(input_data)
    reactive = screen_reactive_power(input_data)

    req_docs, conditions = merge_screening_into_feasibility(
        feasibility.required_documents,
        feasibility.conditions,
        protection,
        network_feedback,
        eeg,
        reactive,
    )
    feasibility = feasibility.model_copy(
        update={"required_documents": req_docs, "conditions": conditions}
    )

    return GridCalculationResult(
        calculated_at=datetime.now(timezone.utc).isoformat(),
        calculation_version=CALCULATION_VERSION,
        assumptions=assumptions,
        voltage_drop_analysis=voltage_drop,
        short_circuit_analysis=short_circuit,
        thermal_analysis=thermal,
        n1_assessment=n1,
        thresholds=thresholds,
        feasibility=feasibility,
        transformer_assessment=transformer_assessment,
        protection_concept_screening=protection,
        network_feedback_screening=network_feedback,
        coincidence_factor_screening=coincidence,
        norm_references_applied=norm_refs,
        eeg_feed_in_screening=eeg,
        reactive_power_screening=reactive,
        projektierer_perspective=None,
    )


def calculate_grid_connection_from_engine(
    eingabe: dict[str, Any],
    *,
    project_id: int | None = None,
) -> dict[str, Any]:
    """Convenience: legacy eingabe → v2 result as JSON-serializable dict."""
    inp = grid_connection_input_from_engine(eingabe)
    anlagentyp = eingabe.get("anlagentyp")
    result = calculate_grid_connection(inp, anlagentyp=str(anlagentyp) if anlagentyp else None)
    perspective_raw = build_projektierer_perspective(
        eingabe, inp, project_id=project_id or eingabe.get("project_id")
    )
    from engine.grid_calculation_types import ProjektiererPerspective

    updated = result.model_copy(
        update={"projektierer_perspective": ProjektiererPerspective.model_validate(perspective_raw)}
    )
    return updated.model_dump()
