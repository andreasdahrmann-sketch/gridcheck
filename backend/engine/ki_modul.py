from __future__ import annotations

import json
import math
import os
from collections import Counter
from typing import Any

from engine.ki_feedback import (
    berechne_kalibrierung,
    berechne_lernstatus,
    feedback_index_nach_revision,
)
from engine.revision import lade_revisionen

KI_DATEN_PFAD = "daten/ki_lerndaten.json"


def lade_lerndaten():
    if not os.path.exists(KI_DATEN_PFAD):
        return []
    try:
        with open(KI_DATEN_PFAD, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _entscheidung_key(fazit):
    if isinstance(fazit, dict):
        return str(fazit.get("entscheidung", "")).strip().upper()
    if isinstance(fazit, str):
        return fazit.split(":")[0].strip().upper()
    return ""


def _float_or_zero(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def berechne_aehnlichkeit(a, b):
    try:
        felder = ["nennspannung", "leistung_mw", "entfernung_km"]
        summe = 0.0
        for feld in felder:
            va = _float_or_zero(a.get(feld))
            vb = _float_or_zero(b.get(feld))
            maxval = max(abs(va), abs(vb), 1.0)
            diff = (va - vb) / maxval
            summe += diff ** 2
        if str(a.get("leitungstyp", "")).strip().upper() != str(b.get("leitungstyp", "")).strip().upper():
            summe += 1.0
        if str(a.get("anschlussart", "")).strip().upper() != str(b.get("anschlussart", "")).strip().upper():
            summe += 0.5
        distanz = math.sqrt(summe)
        aehnlichkeit = max(0.0, 1.0 - distanz / 3.0)
        return round(aehnlichkeit, 4)
    except Exception:
        return 0.0


def _baue_revisions_lernfaelle():
    feedback_by_revision = feedback_index_nach_revision()
    out = []
    for revision in lade_revisionen():
        data = revision.get("daten", {})
        eingabe = data.get("eingabe", {})
        fazit = data.get("fazit", {})
        if not isinstance(eingabe, dict):
            continue
        if _entscheidung_key(fazit) not in {"A", "B", "C"}:
            continue
        out.append(
            {
                "eingabe": eingabe,
                "fazit": fazit,
                "scores": data.get("scores", {}),
                "datenqualitaet": data.get("datenqualitaet", {}),
                "revision_hash": revision.get("hash"),
                "feedback": feedback_by_revision.get(revision.get("hash")),
            }
        )
    return out


def _baue_legacy_lernfaelle():
    out = []
    for eintrag in lade_lerndaten():
        if not isinstance(eintrag, dict):
            continue
        out.append(
            {
                "eingabe": eintrag.get("eingabe", {}),
                "fazit": eintrag.get("fazit", {}),
                "scores": eintrag.get("scores", {}),
                "datenqualitaet": eintrag.get("datenqualitaet", {}),
                "revision_hash": None,
                "feedback": None,
            }
        )
    return out


def lade_lernfaelle():
    revisions_faelle = _baue_revisions_lernfaelle()
    if revisions_faelle:
        return revisions_faelle
    return _baue_legacy_lernfaelle()


def finde_aehnliche(eingabe, lernfaelle, *, current_revision_hash=None, top_n=5):
    scored = []
    for eintrag in lernfaelle:
        if current_revision_hash and eintrag.get("revision_hash") == current_revision_hash:
            continue
        score = berechne_aehnlichkeit(eingabe, eintrag.get("eingabe", {}))
        if score > 0.3:
            scored.append({"score": score, "eintrag": eintrag})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def _feedback_decision(scored_entry):
    feedback = scored_entry["eintrag"].get("feedback") or {}
    return _entscheidung_key(feedback.get("daten", {}).get("nb_entscheidung"))


def bewerte_anomalie(ergebnis, aehnliche):
    flags: list[str] = []
    severity_points = 0
    dq = ergebnis.get("datenqualitaet", {}) or {}
    aktuelles_fazit = _entscheidung_key(ergebnis.get("fazit", {}))
    score_gesamt = _float_or_zero((ergebnis.get("scores", {}) or {}).get("gesamt"))

    if not aehnliche:
        flags.append("Keine belastbaren Vergleichsfaelle vorhanden.")
        severity_points += 2
    else:
        bester_match = aehnliche[0]["score"]
        if bester_match < 0.45:
            flags.append("Nur schwach aehnliche Vergleichsfaelle gefunden.")
            severity_points += 2

        linked = [item for item in aehnliche if item["eintrag"].get("feedback")]
        if linked:
            nb_counter = Counter(_feedback_decision(item) for item in linked if _feedback_decision(item))
            if nb_counter:
                haeufigste_nb, count = nb_counter.most_common(1)[0]
                if haeufigste_nb and aktuelles_fazit and haeufigste_nb != aktuelles_fazit and count >= 2:
                    flags.append("Aktuelles Ergebnis weicht von bestaetigten Vergleichsfaellen ab.")
                    severity_points += 3
            correction_rate = sum(
                1
                for item in linked
                if _entscheidung_key(item["eintrag"].get("fazit", {})) != _feedback_decision(item)
            ) / len(linked)
            if correction_rate >= 0.4 and len(linked) >= 3:
                flags.append("Aehnliche Faelle wurden ueberdurchschnittlich oft nachkorrigiert.")
                severity_points += 2

    if _float_or_zero(dq.get("score")) < 45 and score_gesamt >= 75:
        flags.append("Hoher Score bei begrenzter Datenqualitaet.")
        severity_points += 2

    if severity_points >= 5:
        severity = "hoch"
    elif severity_points >= 3:
        severity = "mittel"
    else:
        severity = "niedrig"

    summary = (
        "Keine auffaellige Abweichung gegenueber bekannten Faellen erkannt."
        if not flags
        else flags[0]
    )
    return {
        "is_anomaly": severity_points >= 3,
        "severity": severity,
        "score": min(100, severity_points * 20),
        "flags": flags,
        "summary": summary,
    }


def berechne_konfidenz(aehnliche, kalibrierung, lernstatus, anomalie):
    if not aehnliche:
        base = 0.28
    else:
        n = len(aehnliche)
        avg_score = sum(a["score"] for a in aehnliche) / n
        base = min(0.78, 0.28 + (n * 0.06) + (avg_score * 0.2))

    linked = [a for a in aehnliche if a["eintrag"].get("feedback")]
    bestaetigt = sum(
        1
        for item in linked
        if _entscheidung_key(item["eintrag"].get("fazit", {})) == _feedback_decision(item)
    )
    linked_quote = (bestaetigt / len(linked)) if linked else 0.0
    evidence_boost = min(0.14, (len(linked) * 0.025) + (linked_quote * 0.06))
    anomaly_penalty = min(0.22, (anomalie.get("score", 0) / 100.0) * 0.22)
    faktor = float(kalibrierung.get("kalibrierungsfaktor", 1.0))

    if lernstatus.get("status") == "MATURE":
        evidence_boost += 0.04
    elif lernstatus.get("status") == "LEARNING":
        evidence_boost += 0.02

    konfidenz = max(0.05, min(0.98, (base * faktor) + evidence_boost - anomaly_penalty))
    return round(konfidenz, 3)


def erzeuge_ki_hinweise(ergebnis, aehnliche, kalibrierung, lernstatus, anomalie):
    hinweise = []
    if not aehnliche:
        hinweise.append("Keine vergleichbaren revisionssicheren Faelle vorhanden. Ergebnis basiert vor allem auf der deterministischen Berechnung.")
    else:
        hinweise.append(f"{len(aehnliche)} aehnliche Vergleichsfaelle gefunden.")
        bester = aehnliche[0]
        hinweise.append(f"Bester Match: Aehnlichkeit {round(bester['score'] * 100, 1)}%.")

    if kalibrierung.get("samples", 0) > 0:
        hinweise.append(
            f"Kalibrierung aktiv ({kalibrierung['samples']} NB-Feedbacks, Faktor {kalibrierung['kalibrierungsfaktor']})."
        )
    else:
        hinweise.append("Kalibrierung inaktiv: noch kein Netzbetreiber-Feedback vorhanden.")

    if lernstatus.get("status") == "MATURE":
        hinweise.append("Lernstatus: reife Feedbackbasis mit belastbarer Rueckkopplung.")
    elif lernstatus.get("status") == "LEARNING":
        hinweise.append("Lernstatus: aktiver Feedback-Loop, Confidence steigt mit weiteren bestaetigten Faellen.")
    elif lernstatus.get("status") == "LOW_SIGNAL":
        hinweise.append("Lernstatus: erste echte Rueckmeldungen vorhanden, aber noch geringe Stichprobe.")

    if anomalie.get("flags"):
        hinweise.append("Anomalie-Hinweis: " + anomalie["summary"])

    return hinweise


def ki_bewertung(ergebnis):
    lernfaelle = lade_lernfaelle()
    eingabe = ergebnis.get("eingabe", {})
    current_revision_hash = (ergebnis.get("revision") or {}).get("hash")

    aehnliche = finde_aehnliche(eingabe, lernfaelle, current_revision_hash=current_revision_hash)
    kalibrierung = berechne_kalibrierung()
    lernstatus = berechne_lernstatus()
    anomalie = bewerte_anomalie(ergebnis, aehnliche)
    konfidenz = berechne_konfidenz(aehnliche, kalibrierung, lernstatus, anomalie)
    hinweise = erzeuge_ki_hinweise(ergebnis, aehnliche, kalibrierung, lernstatus, anomalie)

    ergebnis["ki"] = {
        "konfidenz": konfidenz,
        "konfidenz_prozent": round(konfidenz * 100, 1),
        "aehnliche_faelle": len(aehnliche),
        "kalibrierung": kalibrierung,
        "feedback_loop": lernstatus,
        "anomalie_check": anomalie,
        "hinweise": hinweise,
    }

    transparenz = ergebnis.setdefault("transparenz", {})
    notes = list(transparenz.get("confidence_notes", []))
    notes.append(f"KI-Konfidenz {round(konfidenz * 100, 1)}% bei {len(aehnliche)} aehnlichen Vergleichsfaellen.")
    notes.append(
        f"Feedback-Loop {lernstatus.get('status', 'NO_FEEDBACK')}: {lernstatus.get('samples_total', 0)} NB-Feedbacks, "
        f"Bestaetigungsquote {round(float(lernstatus.get('bestaetigungsquote', 0.0)) * 100, 1)}%."
    )
    if anomalie.get("flags"):
        notes.append("Anomalie-Check: " + anomalie["summary"])
    transparenz["confidence_notes"] = [note for note in notes if note]

    return ergebnis
