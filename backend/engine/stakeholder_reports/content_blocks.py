"""
Shared extraction of report sections from engine results (PDF + HTML stakeholders).
"""
from __future__ import annotations

from typing import Any

from engine.plant_types import PLANT_TYPE_CONFIG, resolve_plant_context

_FEED_IN_CLASS_LABELS = {
    "none": "EEG §9 2023: unter 25 kW AC (kein Einspeisemanagement)",
    "remote_control": "EEG §9 2023: 25–<100 kW AC (Fernsteuerbarkeit prüfen)",
    "direct_marketing": "EEG §9 2023: ≥100 kW AC (Direktvermarktung / Bilanzkreis)",
}

_VNB_REVIEW_DEFAULT = "offen — VNB-Prüfung / Nachreichung Netzdaten"


def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _fmt_num(value: Any, *, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if suffix:
        return f"{num:.{digits}f}{suffix}"
    return f"{num:.{digits}f}"


def _plant_label_from_eingabe(eingabe: dict[str, Any]) -> str:
    try:
        ctx = resolve_plant_context(eingabe)
        return ctx.config.label
    except Exception:
        raw = str(eingabe.get("anlagentyp") or eingabe.get("plant_type") or "").strip().lower()
        for pt, cfg in PLANT_TYPE_CONFIG.items():
            if pt.value == raw:
                return cfg.label
        return raw or "Anlage"


def _grid_v2(engine_result: dict[str, Any]) -> dict[str, Any]:
    v2 = engine_result.get("grid_calculation_v2")
    return v2 if isinstance(v2, dict) else {}


def _projektierer_perspective(engine_result: dict[str, Any]) -> dict[str, Any] | None:
    persp = _grid_v2(engine_result).get("projektierer_perspective")
    return persp if isinstance(persp, dict) else None


def build_technical_details_table(engine_result: dict[str, Any]) -> list[dict[str, str]]:
    """Rows for Kenngröße | Wert | Hinweis tables in Projektierer/VNB PDFs."""
    td = engine_result.get("technical_details")
    if not isinstance(td, dict):
        td = {}

    sp = td.get("spannungsfall") if isinstance(td.get("spannungsfall"), dict) else {}
    ks = td.get("kurzschluss") if isinstance(td.get("kurzschluss"), dict) else {}
    lei = td.get("leitung") if isinstance(td.get("leitung"), dict) else {}
    tr = td.get("trasse") if isinstance(td.get("trasse"), dict) else {}

    thermisch = engine_result.get("thermisch") if isinstance(engine_result.get("thermisch"), dict) else {}
    spannung = engine_result.get("spannung") if isinstance(engine_result.get("spannung"), dict) else {}
    kurzschluss = engine_result.get("kurzschluss") if isinstance(engine_result.get("kurzschluss"), dict) else {}

    rows: list[dict[str, str]] = [
        {
            "kenngroesse": "Spannungsfall ΔU",
            "wert": f"{_fmt_num(sp.get('delta_u_prozent'), digits=2, suffix=' %')}",
            "hinweis": " ".join(
                x
                for x in [
                    str(sp.get("bewertung") or spannung.get("bewertung") or ""),
                    str(sp.get("cos_phi_annahme") or ""),
                    str(spannung.get("text") or "")[:120],
                ]
                if x
            )
            or "Vorläufiges Screening",
        },
        {
            "kenngroesse": "Kurzschluss Ik",
            "wert": _fmt_num(
                ks.get("ik_referenz_ka") or ks.get("ik_max_ka") or kurzschluss.get("ik_max_ka"),
                digits=1,
                suffix=" kA",
            ),
            "hinweis": (
                "Vorläufig (Band)"
                if ks.get("vorlaeufig")
                else str(ks.get("hinweis") or kurzschluss.get("text") or "")[:160]
            ),
        },
        {
            "kenngroesse": "Leitung / Querschnitt",
            "wert": (
                f"{lei.get('querschnitt_mm2')} mm²"
                if lei.get("querschnitt_mm2") is not None
                else str(lei.get("typ") or "n/a")
            ),
            "hinweis": " ".join(
                x
                for x in [
                    str(lei.get("typ") or ""),
                    f"Imax {lei['i_max_a']} A" if lei.get("i_max_a") is not None else "",
                    str(thermisch.get("bewertung") or ""),
                ]
                if x
            )[:160],
        },
        {
            "kenngroesse": "Trasse / Entfernung",
            "wert": _fmt_num(tr.get("entfernung_km"), digits=2, suffix=" km"),
            "hinweis": (
                "Heuristische Entfernung"
                if tr.get("heuristisch")
                else str(tr.get("annahme") or "Nutzereingabe")[:160]
            ),
        },
    ]
    return rows


def build_vnb_technical_review_table(engine_result: dict[str, Any]) -> list[dict[str, str]]:
    """Kenngröße | Screening | VNB-Prüfung — third column left open for operator."""
    rows: list[dict[str, str]] = []
    for item in build_technical_details_table(engine_result):
        rows.append(
            {
                "kenngroesse": item["kenngroesse"],
                "screening": item["wert"],
                "vnb_pruefung": _VNB_REVIEW_DEFAULT,
                "hinweis": item["hinweis"],
            }
        )

    precheck = engine_result.get("thermisch"), engine_result.get("spannung"), engine_result.get("kurzschluss")
    labels = ("Thermik", "Spannung", "Kurzschluss")
    for label, block in zip(labels, precheck, strict=True):
        if not isinstance(block, dict):
            continue
        rows.append(
            {
                "kenngroesse": label,
                "screening": str(block.get("bewertung") or "OFFEN"),
                "vnb_pruefung": _VNB_REVIEW_DEFAULT,
                "hinweis": str(block.get("text") or "")[:160],
            }
        )
    n1 = engine_result.get("n1") if isinstance(engine_result.get("n1"), dict) else {}
    rows.append(
        {
            "kenngroesse": "N-1-Screening",
            "screening": str(n1.get("n1_klasse") or n1.get("bewertung") or "N1-0"),
            "vnb_pruefung": _VNB_REVIEW_DEFAULT,
            "hinweis": str(n1.get("detail_text") or n1.get("topologie_text") or "")[:160],
        }
    )
    return rows


def build_vnb_signature_section() -> dict[str, Any]:
    """Static PDF layout placeholders — no electronic signature."""
    return {
        "title": "VNB-Prüfung / Freigabe (Formularfeld)",
        "fields": [
            {"label": "Zuständiger Netzbetreiber", "placeholder": "________________________________"},
            {"label": "Bearbeiter / Sachbearbeitung", "placeholder": "________________________________"},
            {"label": "Datum der Vorprüfung", "placeholder": "________________________________"},
            {"label": "Ergebnis / Auflagen (Kurztext)", "placeholder": "________________________________"},
            {"label": "Unterschrift / Stempel VNB", "placeholder": "________________________________"},
        ],
        "disclaimer": (
            "Dieser Abschnitt ist ein statisches Formularfeld im PDF-Layout. "
            "Er ersetzt keine digitale Signatur und keine verbindliche Netzanschlussentscheidung."
        ),
    }


def build_eeg_checklist(engine_result: dict[str, Any]) -> list[str]:
    """EEG §9 oriented checklist lines from grid_calculation_v2 when present."""
    v2 = _grid_v2(engine_result)
    items: list[str] = []
    persp = _projektierer_perspective(engine_result)
    fic = None
    if persp:
        fic = persp.get("feed_in_management_class")
        if fic:
            items.append(_FEED_IN_CLASS_LABELS.get(str(fic), f"Einspeisemanagement-Klasse: {fic}"))

    eeg = v2.get("eeg_feed_in_screening")
    if isinstance(eeg, dict) and eeg.get("applicable"):
        if eeg.get("feed_in_management_class") and not any("EEG" in x for x in items):
            items.append(
                _FEED_IN_CLASS_LABELS.get(
                    str(eeg["feed_in_management_class"]),
                    str(eeg["feed_in_management_class"]),
                )
            )
        for req in _as_text_list(eeg.get("required_measures")):
            items.append(f"EEG — erforderlich: {req}")
        for hint in _as_text_list(eeg.get("hints")):
            items.append(f"EEG — Hinweis: {hint}")
        for cond in _as_text_list(eeg.get("conditions")):
            items.append(f"EEG — Bedingung: {cond}")

    if not items:
        items.append(
            "EEG §9 2023: Einspeisemanagement-Klasse aus AC-Leistung prüfen "
            "(<25 kW / 25–<100 kW Fernsteuerung / ≥100 kW Direktvermarktung)."
        )
    return items[:12]


def build_reactive_checklist(engine_result: dict[str, Any]) -> list[str]:
    v2 = _grid_v2(engine_result)
    reactive = v2.get("reactive_power_screening")
    if not isinstance(reactive, dict) or not reactive.get("applicable"):
        return []
    out: list[str] = []
    for item in reactive.get("checklist") or []:
        if isinstance(item, dict) and item.get("topic"):
            out.append(f"{item['topic']}: {item.get('note', '')}")
    return out[:8]


def build_process_timeline_lines(engine_result: dict[str, Any]) -> list[str]:
    persp = _projektierer_perspective(engine_result)
    if not persp:
        return []
    tl = persp.get("process_timeline") or {}
    if not isinstance(tl, dict):
        return []
    lines: list[str] = []
    if tl.get("estimated_total"):
        lines.append(f"Gesamt (heuristisch): {tl['estimated_total']}")
    for phase in tl.get("phases") or []:
        if not isinstance(phase, dict):
            continue
        name = phase.get("phase") or phase.get("name") or "Phase"
        dur = phase.get("duration_weeks") or phase.get("duration") or "?"
        resp = phase.get("responsible") or ""
        line = f"{name}: {dur} Wochen"
        if resp:
            line += f" ({resp})"
        lines.append(line)
    if tl.get("disclaimer"):
        lines.append(str(tl["disclaimer"]))
    return lines


def build_bkz_hint_text(engine_result: dict[str, Any]) -> str | None:
    persp = _projektierer_perspective(engine_result)
    if not persp:
        return None
    bkz = persp.get("bkz_hint") or {}
    if isinstance(bkz, dict) and bkz.get("hint"):
        return str(bkz["hint"])
    return None


def build_invest_kpi_summary(engine_result: dict[str, Any]) -> list[str]:
    fazit = engine_result.get("fazit") if isinstance(engine_result.get("fazit"), dict) else {}
    scores = engine_result.get("scores") if isinstance(engine_result.get("scores"), dict) else {}
    n1 = engine_result.get("n1") if isinstance(engine_result.get("n1"), dict) else {}
    kosten = engine_result.get("kosten") if isinstance(engine_result.get("kosten"), dict) else {}
    eingabe = engine_result.get("eingabe") if isinstance(engine_result.get("eingabe"), dict) else {}

    lines = [
        f"Entscheidung Screening: {fazit.get('entscheidung', 'C')}",
        f"Gesamt-Score: {scores.get('gesamt', 'n/a')}/100",
        f"N-1-Klasse: {n1.get('n1_klasse', 'N1-0')}",
        f"Leistung: {_fmt_num(eingabe.get('leistung_mw'), digits=3, suffix=' MW')}",
    ]
    basis = kosten.get("band_basis_eur") or kosten.get("investition_gesamt_eur")
    if basis is not None:
        low = kosten.get("band_niedrig_eur") or basis
        high = kosten.get("band_hoch_eur") or basis
        lines.append(f"Kostenband (EUR): {low} – {high} (Basis {basis})")
    stakeholder = engine_result.get("stakeholder_bewertung")
    if isinstance(stakeholder, dict):
        avg = round(
            (
                float(stakeholder.get("netzbetreiber_score", 0))
                + float(stakeholder.get("projektierer_score", 0))
                + float(stakeholder.get("umsetzung_score", 0))
            )
            / 3,
            1,
        )
        lines.append(f"Stakeholder-Fit (Mittel): {avg}/100")
    return lines
