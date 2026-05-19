"""
Netzbetreiber-Akzeptanz Screening (Gaps 6–12) — transparente Bewertungen ohne Scheinberechnungen.

Keine freie Trafo-Kapazität, keine Pass/Fail-Aussagen ohne belastbare Daten.
"""
from __future__ import annotations


from engine.grid_calculation_types import (
    CalculationAssumption,
    CoincidenceFactorScreening,
    EegFeedInScreening,
    GridConnectionInput,
    NetworkFeedbackScreening,
    NetworkFeedbackTopic,
    NormReference,
    ProtectionChecklistItem,
    ProtectionConceptScreening,
    TransformerAssessment,
)

NS_COINCIDENCE_WARNING_KW = 30.0
EEG_REMOTE_CONTROL_KW = 25.0
EEG_DIRECT_MARKETING_KW = 100.0


def _vde_ar_n_generation_ref(voltage_level: str) -> str:
    if voltage_level == "low":
        return "VDE-AR-N 4105:2018-11"
    if voltage_level == "high":
        return "VDE-AR-N 4120:2018-11"
    return "VDE-AR-N 4110:2018-11"


def build_norm_references_applied(
    input_data: GridConnectionInput,
) -> list[NormReference]:
    refs: list[NormReference] = []
    vl = input_data.voltage_level
    pt = input_data.project_type

    if pt in ("generation", "storage", "mixed"):
        code = _vde_ar_n_generation_ref(vl)
        title = {
            "VDE-AR-N 4105:2018-11": "Erzeugungsanlagen an Niederspannung",
            "VDE-AR-N 4110:2018-11": "Erzeugungsanlagen an Mittelspannung",
            "VDE-AR-N 4120:2018-11": "Erzeugungsanlagen an Hochspannung",
        }[code]
        refs.append(
            NormReference(
                code=code,
                title=title,
                applied_to="Einspeiseanlage, Schutzkonzept, Netzrückwirkungen (Screening)",
            )
        )

    if pt == "consumption" and vl == "low":
        refs.append(
            NormReference(
                code="VDE-AR-N 4100:2019-11",
                title="Technische Anschlussregeln Niederspannung (Verbraucher)",
                applied_to="Verbraucheranschluss, Leitungsdimensionierung",
            )
        )

    refs.append(
        NormReference(
            code="EN 50160:2010",
            title="Spannungsmerkmale in öffentlichen Elektrizitätsversorgungsnetzen",
            applied_to="Spannungsqualität, Spannungsänderungen (Richtwerte)",
        )
    )
    refs.append(
        NormReference(
            code="IEC 60909-0:2016",
            title="Kurzschlussströme in Drehstromnetzen",
            applied_to="Kurzschlussnachweis (Hinweis — vollständige Berechnung nur mit Netzdaten)",
        )
    )

    if pt in ("generation", "storage", "mixed"):
        refs.extend(
            [
                NormReference(
                    code="EN 61000-3-2",
                    title="Grenzwerte für Oberschwingungsströme",
                    applied_to="Erzeugungsanlagen / netzbetreibende Geräte",
                ),
                NormReference(
                    code="EN 61000-3-3",
                    title="Grenzwerte für Spannungsänderungen, Schwankungen und Flicker",
                    applied_to="Einspeisung, Lastwechsel",
                ),
            ]
        )
        if pt in ("storage", "mixed") or input_data.power_kw >= 100:
            refs.append(
                NormReference(
                    code="IEC 61000-3-11",
                    title="Flicker — Schwankungen durch Lasten > 75 A",
                    applied_to="Große BESS / Lastwechsel (Screening-Hinweis)",
                )
            )

    refs.append(
        NormReference(
            code="EEG 2023",
            title="Erneuerbare-Energien-Gesetz (Fernsteuerbarkeit, Einspeisemanagement)",
            applied_to="Einspeisemanagement ab 25 kW, Direktvermarktung ab 100 kW",
        )
    )
    return refs


def assess_transformer_loading(
    input_data: GridConnectionInput,
    assumptions: list[CalculationAssumption],
) -> TransformerAssessment:
    required = ["transformer_power_kva", "transformer_load_percent"]
    missing: list[str] = []
    if input_data.transformer_power_kva is None:
        missing.append("transformer_power_kva (Trafo-Nennleistung kVA)")
    if input_data.transformer_load_percent is None:
        missing.append("transformer_load_percent (Bestandsauslastung %, VNB/Planer)")

    if missing:
        return TransformerAssessment(
            status="insufficient_data",
            required_fields=required,
            missing_fields=missing,
            disclaimer=(
                "Ohne Trafo-Nennleistung und dokumentierte Bestandsauslastung ist keine "
                "belastbare Auslastungsbewertung möglich. Es wird keine Schein-Auslastung in % ausgegeben."
            ),
        )

    s_nom_kva = input_data.transformer_power_kva
    load_pct = input_data.transformer_load_percent
    p_kw = input_data.power_kw

    if input_data.project_type == "consumption":
        additional_kva = p_kw / max(input_data.power_factor, 0.8)
    else:
        additional_kva = p_kw / max(input_data.power_factor, 0.8)

    existing_kva = s_nom_kva * (load_pct / 100.0)
    screened_total_kva = existing_kva + additional_kva
    screened_utilization_pct = (screened_total_kva / s_nom_kva) * 100.0

    assumptions.append(
        CalculationAssumption(
            parameter="Trafo-Auslastung (Screening)",
            assumed_value=(
                f"Bestand {load_pct:.1f}% + Projekt {additional_kva:.1f} kVA "
                f"≈ {screened_utilization_pct:.1f}% von {s_nom_kva:.0f} kVA"
            ),
            reason=(
                "Konservatives Screening: Scheinleistung aus P/cos φ, keine N-1-Reserve, "
                "keine Blindleistungsführung — keine freie Kapazität abgeleitet."
            ),
            norm_reference="VNB-ONT / technische Anschlussbedingungen",
            confidence="low",
        )
    )

    notes: list[str] = []
    if screened_utilization_pct > 100:
        notes.append(
            f"Screening: rechnerische Gesamtauslastung {screened_utilization_pct:.1f}% "
            f"über 100% — VNB-Lastfluss und ONT-Prüfung erforderlich."
        )
    elif screened_utilization_pct > 80:
        notes.append(
            f"Screening: Auslastung {screened_utilization_pct:.1f}% — Reserve und N-1 beim VNB klären."
        )

    return TransformerAssessment(
        status="screened",
        required_fields=required,
        missing_fields=[],
        transformer_power_kva=s_nom_kva,
        existing_load_percent=load_pct,
        project_apparent_kva=round(additional_kva, 1),
        screened_total_utilization_percent=round(screened_utilization_pct, 1),
        screening_notes=notes,
        disclaimer=(
            "Konservatives Plausibilitäts-Screening auf Basis der Eingaben — keine verbindliche "
            "Trafo-Kapazitätsaussage und keine Ersatz für ONT-/Lastflussnachweise des Netzbetreibers."
        ),
    )


def screen_protection_concept(input_data: GridConnectionInput) -> ProtectionConceptScreening:
    if input_data.project_type not in ("generation", "storage", "mixed"):
        return ProtectionConceptScreening(
            applicable=False,
            voltage_level_ref=_vde_ar_n_generation_ref(input_data.voltage_level),
            checklist=[],
            required_documents=[],
            disclaimer="Schutzkonzept-Screening gilt nur für Einspeiseanlagen (Erzeugung/Speicher).",
        )

    vde_ref = _vde_ar_n_generation_ref(input_data.voltage_level)
    checklist = [
        ProtectionChecklistItem(
            topic="NA-Schutz / Entkupplung",
            norm_reference=vde_ref,
            status="requires_verification",
            note=(
                "Netz- und Anlagenschutz, Entkupplung bei Netzstörungen — Einstellung und "
                "Koordination durch VNB/Planer, nicht berechnet."
            ),
        ),
        ProtectionChecklistItem(
            topic="Einstellwerte U>, U<, f>, f<",
            norm_reference=vde_ref,
            status="requires_configuration",
            note=(
                "Schutz- und Überwachungsgrenzwerte müssen projektiert und mit dem VNB "
                "abgestimmt werden — keine automatische Berechnung in dieser Vorprüfung."
            ),
        ),
        ProtectionChecklistItem(
            topic="Wechselrichter-Zertifizierung",
            norm_reference="VDE-AR-N 4105:2018-11 (NS-Erzeugung)" if input_data.voltage_level == "low" else vde_ref,
            status="requires_documentation",
            note="Nachweis der Konformität der Erzeugungseinheit (z. B. VDE-AR-N 4105 Zertifikat / Einheitenzertifikat).",
        ),
    ]

    docs = [
        "Schutzkonzept / Schutzplan (Einspeiseanlage)",
        "Einstellwerte und Schutzkoordination (VNB-Abstimmung)",
        "Nachweis Wechselrichter- bzw. Erzeugerzertifizierung",
        f"Technische Richtlinie {vde_ref}",
    ]

    return ProtectionConceptScreening(
        applicable=True,
        voltage_level_ref=vde_ref,
        checklist=checklist,
        required_documents=docs,
        disclaimer=(
            "Checkliste ohne Pass/Fail — fehlende Unterlagen und Studien sind beim VNB "
            "vor Netzanschlussbegehren zu klären."
        ),
    )


def _is_network_feedback_relevant(input_data: GridConnectionInput, anlagentyp: str | None) -> bool:
    if input_data.project_type in ("generation", "storage", "mixed"):
        return True
    industrial_types = {"waermepumpe", "ladepark", "sonstiges"}
    return str(anlagentyp or "").lower() in industrial_types


def screen_network_feedback(
    input_data: GridConnectionInput,
    anlagentyp: str | None = None,
) -> NetworkFeedbackScreening:
    if not _is_network_feedback_relevant(input_data, anlagentyp):
        return NetworkFeedbackScreening(
            applicable=False,
            cannot_quantify=False,
            topics=[],
            recommended_studies=[],
            disclaimer="Netzrückwirkungs-Screening für reinen Verbraucheranschluss nicht aktiv.",
        )

    topics: list[NetworkFeedbackTopic] = [
        NetworkFeedbackTopic(
            standard="EN 61000-3-2",
            subject="Oberschwingungen",
            screening_level="qualitative",
            warning=(
                "Oberschwingungsströme der Erzeugungs-/Lastanlage können Grenzwerte "
                "beeinflussen — Nachweis typischerweise über Herstellerdaten und VNB-Studie."
            ),
        ),
        NetworkFeedbackTopic(
            standard="EN 61000-3-3",
            subject="Spannungsänderungen / Flicker (allgemein)",
            screening_level="qualitative",
            warning=(
                "Spannungsänderungen durch Einspeisung oder Lastwechsel — ohne Messdaten "
                "keine quantitative Bewertung."
            ),
        ),
    ]

    if input_data.project_type in ("storage", "mixed") or input_data.power_kw >= 75:
        topics.append(
            NetworkFeedbackTopic(
                standard="IEC 61000-3-11",
                subject="Flicker (große Anlage / BESS)",
                screening_level="qualitative",
                warning=(
                    "Große BESS oder schnelle Leistungswechsel können erhöhtes Flicker-Risiko "
                    "bedeuten — Lastfluss- und Flickerstudie beim VNB empfohlen."
                ),
            )
        )

    return NetworkFeedbackScreening(
        applicable=True,
        cannot_quantify=True,
        topics=topics,
        recommended_studies=[
            "Netzrückwirkungsstudie / Einhaltungsnachweis EN 61000-3-x (VNB oder Planer)",
            "Messkonzept am Point of Common Coupling (PCC)",
        ],
        disclaimer=(
            "Ohne Mess- und Netzdaten des Betreibers sind keine quantitativen Grenzwertnachweise "
            "möglich — nur qualitative Screening-Hinweise."
        ),
    )


def screen_coincidence_factor(
    input_data: GridConnectionInput,
    assumptions: list[CalculationAssumption],
) -> CoincidenceFactorScreening:
    assumptions.append(
        CalculationAssumption(
            parameter="Gleichzeitigkeitsfaktor",
            assumed_value="1,0 (Einzelanschluss)",
            reason=(
                "Diese Vorprüfung betrachtet nur den einzelnen Netzanschlusspunkt. "
                "Kumulative Effekte weiterer Anlagen im gleichen NS-Segment sind nicht modelliert."
            ),
            norm_reference="VNB-Lastfluss / Planungsrichtlinien",
            confidence="high",
        )
    )

    warnings: list[str] = []
    if input_data.voltage_level == "low" and input_data.power_kw > NS_COINCIDENCE_WARNING_KW:
        warnings.append(
            f"Leistung {input_data.power_kw:.0f} kW im NS: kumulative Wirkung weiterer Anlagen "
            f"im gleichen NS-Segment erfordert VNB-Lastfluss — Gleichzeitigkeit nicht angenommen."
        )

    return CoincidenceFactorScreening(
        single_connection_analysis=True,
        cluster_modeling_available=False,
        warnings=warnings,
        disclaimer=(
            "Mehrere Anlagen am gleichen Ortsnetztransformator oder Strang werden nicht "
            "automatisch addiert — Cluster- und Gleichzeitigkeitsfaktoren sind VNB-Aufgabe."
        ),
    )


def grid_form_note(input_data: GridConnectionInput) -> str:
    topo = input_data.grid_topology
    cable = input_data.cable_type
    topo_de = {
        "radial": "Strahlnetz (radial)",
        "ring": "Ringnetz",
        "meshed": "Vermaschtes Netz",
        "unknown": "unbekannt",
    }.get(topo, topo)
    cable_de = "Kabel" if cable == "underground" else "Freileitung"
    return (
        f"Netzform (Annahme): {topo_de}, Leitungsführung: {cable_de}. "
        f"R/X-Verhältnis im Spannungsfall-Screening folgt dieser Annahme."
    )


def screen_eeg_feed_in(input_data: GridConnectionInput) -> EegFeedInScreening:
    if input_data.project_type not in ("generation", "storage", "mixed"):
        return EegFeedInScreening(
            applicable=False,
            power_kw=input_data.power_kw,
            warnings=[],
            required_documents=[],
            hints=[],
        )

    warnings: list[str] = []
    docs: list[str] = []
    hints: list[str] = []

    if input_data.power_kw >= EEG_REMOTE_CONTROL_KW:
        warnings.append(
            f"EEG 2023: Anlage ≥ {EEG_REMOTE_CONTROL_KW:.0f} kW — Fernsteuerbarkeit und "
            f"Einspeisemanagement nach § 9 EEG mit Netzbetreiber abstimmen."
        )
        docs.append("Nachweis Fernsteuerbarkeit / Steuerbarkeit (§ 9 EEG 2023)")
        hints.append("§ 9 EEG: Einspeisemanagement, Abregelbarkeit, Kommunikationsschnittstelle zum VNB")

    if input_data.power_kw >= EEG_DIRECT_MARKETING_KW:
        hints.append(
            f"EEG 2023: Ab {EEG_DIRECT_MARKETING_KW:.0f} kW typischerweise Direktvermarktung "
            f"und Marktprämienmodell prüfen (wirtschaftlich, nicht Netztechnik)."
        )
        docs.append("Direktvermarktungs- / Marktintegrationskonzept (≥ 100 kW)")

    return EegFeedInScreening(
        applicable=True,
        power_kw=input_data.power_kw,
        remote_control_threshold_kw=EEG_REMOTE_CONTROL_KW,
        direct_marketing_hint_threshold_kw=EEG_DIRECT_MARKETING_KW,
        warnings=warnings,
        required_documents=docs,
        hints=hints,
        disclaimer=(
            "Hinweise auf EEG 2023 (nicht § 8 EEG a.F.) — keine Rechtsberatung, "
            "verbindliche Auslegung beim VNB und ggf. Rechtsberatung."
        ),
    )


def merge_screening_into_feasibility(
    feasibility_docs: list[str],
    feasibility_warnings: list[str],
    protection: ProtectionConceptScreening,
    network_feedback: NetworkFeedbackScreening,
    eeg: EegFeedInScreening,
) -> tuple[list[str], list[str]]:
    docs = list(feasibility_docs)
    conditions = list(feasibility_warnings)

    if protection.applicable:
        for d in protection.required_documents:
            if d not in docs:
                docs.append(d)

    if network_feedback.applicable:
        for s in network_feedback.recommended_studies:
            if s not in docs:
                docs.append(s)

    if eeg.applicable:
        for w in eeg.warnings:
            conditions.append(w)
        for d in eeg.required_documents:
            if d not in docs:
                docs.append(d)

    return docs, conditions
