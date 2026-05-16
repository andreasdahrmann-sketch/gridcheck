# GridCheck KI-Lernmodul – Was „Training“ hier bedeutet

**Stand:** 2026-05-16  
**Kurzantwort:** Es gibt **kein trainiertes ML-Modell** (kein Fine-Tuning, keine Modell-Weights, keine OpenAI-Anbindung). Das „Lernmodul“ ist ein **regelbasiertes Feedback- und Vergleichssystem** auf revisionssicheren Analysen. „Training“ = **Daten sammeln** (Analysen + Netzbetreiber-Feedback), bis Kalibrierung und ähnliche Fälle belastbar werden.

---

## 1. Was existiert heute (Grundgerüst)

| Komponente | Zweck | Ort |
|------------|--------|-----|
| Deterministische Engine | Normnahe Berechnung, Fazit A/B/C | `backend/engine/berechnung.py` |
| KI-Schicht (unterstützend) | Ähnlichkeit, Konfidenz, Anomalie-Hinweise | `backend/engine/ki_modul.py` |
| Feedback-Speicher | NB-Rückmeldung, Hash-Kette | PostgreSQL `ki_feedback_records` |
| Feedback-API | CRUD-ähnlich + Status | `backend/api/v1_ki_feedback.py` |
| Legacy-Demo-Fälle | Fallback ohne Revisionen | `backend/daten/ki_lerndaten.json` |
| UI | Anzeige + VNB-Feedback-Formular | `frontend/components/GridCheckForm.tsx` |

Nach jeder erfolgreichen Analyse ruft die Engine `ki_bewertung()` auf (`backend/engine/__init__.py`, `services/v1_analysis_service.py`). Das Ergebnis enthält ein Objekt `ki` mit u. a. `konfidenz_prozent`, `aehnliche_faelle`, `kalibrierung`, `feedback_loop`, `anomalie_check`, `hinweise`.

**Wichtig (Projektprinzip):** Die KI-Schicht **ersetzt nicht** die deterministische Normprüfung. Sie kennzeichnet sich in der UI als „unterstützend / assoziativ“ und darf keine verbindliche Netzentscheidung suggerieren (`docs/RISIKO_STATUS.md` R-07).

---

## 2. Was „Training“ in GridCheck **nicht** ist

- Kein `sklearn` / PyTorch / TensorFlow im App-Code
- Keine OpenAI- oder andere Paid-LLM-Integration für das Lernmodul
- Kein `train.py`, kein Export für Fine-Tuning, keine deploybaren `model.pkl`-Dateien
- Keine automatische Änderung der Berechnungslogik aus Feedback

---

## 3. Was „Training“ in GridCheck **tatsächlich** ist

Drei ineinandergreifende Mechanismen:

### 3.1 Lernfälle (Vergleichsfälle)

Quelle (Priorität):

1. **Revisionssichere Analysen** mit Fazit `A`, `B` oder `C` in `revision_records` (über `engine.revision.lade_revisionen()`).
2. Falls keine Revisionen: Fallback auf **`daten/ki_lerndaten.json`** (Seed/Demo-Fälle).

Pro Fall werden u. a. `nennspannung`, `leistung_mw`, `entfernung_km`, `leitungstyp`, `anschlussart` für **Ähnlichkeits-Score** genutzt (`berechne_aehnlichkeit` in `ki_modul.py`).

### 3.2 Netzbetreiber-Feedback (Kalibrierung)

Feedback wird in **`ki_feedback_records`** gespeichert (append-only Hash-Kette, Schema `1.2.0`).

Felder in `data_json` (kanonisch):

- `feedback_typ`: `bestaetigt` | `korrigiert`
- `ki_entscheidung` / `nb_entscheidung`: `A` | `B` | `C`
- `revision_hash`: SHA-256 der Analyse-Revision (Pflicht bei API)
- optional: `score_gesamt`, `confidence_snapshot`, `anomaly_flags`, `kommentar`, `quelle`

**Kalibrierung** (`berechne_kalibrierung`): aus allen KI-vs.-NB-Paaren wird u. a. `trefferquote`, `bias`, `kalibrierungsfaktor` (ca. 0,75–1,08) berechnet und in die KI-Konfidenz einbezogen.

**Lernstatus** (`berechne_lernstatus`):

| `samples_total` | `status` |
|-----------------|----------|
| 0 | `NO_FEEDBACK` |
| 1–4 | `LOW_SIGNAL` |
| 5–19 | `LEARNING` |
| ≥ 20 | `MATURE` |

### 3.3 Laufzeit-Hinweise

- **Anomalie-Check:** Abweichung zu ähnlichen Fällen mit NB-Feedback, hoher Score bei schwacher Datenqualität, etc.
- **Konfidenz:** Heuristik aus Anzahl/Qualität ähnlicher Fälle, Kalibrierungsfaktor, Lernstatus, Anomalie-Penalty.

---

## 4. Schritt-für-Schritt: So „trainieren“ Sie das Modul operativ

### Phase A – Analysen erzeugen (Lernfall-Basis)

1. Backend + PostgreSQL laufen (lokal z. B. Docker, Port 5433).
2. Migrationen: `alembic upgrade head` im `backend/`-Verzeichnis.
3. Im Frontend (Stakeholder **Projektierer** oder mit Schreibrecht) eine **echte Analyse** durchführen (`POST /api/v1/analyze` über die App).
4. Ergebnis muss `revision.hash` und Fazit `A`/`B`/`C` enthalten – nur dann wird der Fall in `lade_lernfaelle()` genutzt.

Ohne Revisionen nutzt das System nur `ki_lerndaten.json` (Demo) – Konfidenz und „ähnliche Fälle“ sind dann weniger aussagekräftig.

### Phase B – Netzbetreiber-Feedback erfassen

**In der UI (empfohlen):**

1. Stakeholder-Pfad **„Netzbetreiber“ / VNB** wählen (Feedback-Block ist nur dort sichtbar).
2. Nach Analyse: Bereich **„Netzbetreiber-Feedback / Lernmodul“**.
3. `bestaetigt`: NB-Entscheidung = KI-Entscheidung (automatisch).
4. `korrigiert`: explizit andere `nb_entscheidung` wählen + Kommentar.
5. **„Feedback speichern“** – verknüpft mit `revision_hash`.

**Per API (curl):**

```bash
# 1) Login (Access-Token)
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"ihr@user.de","password":"IhrPasswort!"}' | jq -r .access_token)

# 2) CSRF-Cookie aus Browser-Session oder Login-Flow – bei API-Tests ggf. Cookie-Jar nutzen

# 3) Feedback (revision_hash aus Analyse-Ergebnis, 64 hex Zeichen)
curl -s -X POST "http://localhost:8000/api/v1/ki/feedback" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <csrf-aus-cookie>" \
  -d '{
    "feedback_typ": "korrigiert",
    "ki_entscheidung": "A",
    "nb_entscheidung": "B",
    "revision_hash": "<64-stelliger-revision-hash>",
    "score_gesamt": 78,
    "confidence_snapshot": 64,
    "anomaly_flags": [],
    "kommentar": "VNB fordert Auflagen.",
    "quelle": "netzbetreiber"
  }'
```

**Antwort (200):** `feedback`, `kalibrierung`, `lernstatus`, `audit_revision`.

### Phase C – Fortschritt prüfen (Admin)

| Endpoint | Beschreibung |
|----------|----------------|
| `GET /api/v1/ki/calibration` | Kalibrierungsfaktor, Trefferquote |
| `GET /api/v1/ki/learning-status` | LOW_SIGNAL / LEARNING / MATURE |
| `GET /api/v1/ki/count` | Anzahl Feedbacks |
| `GET /api/v1/ki/verify` | Integrität der Hash-Kette |
| `GET /api/v1/ki/revision/{hash}` | Feedback zu einer Analyse |

Alle Admin-GETs erfordern Rolle **`admin`** + Bearer-Token.

```bash
curl -s "http://localhost:8000/api/v1/ki/learning-status" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Phase D – Wirkung in neuen Analysen

Bei der **nächsten** Analyse mit ähnlichen Eingaben:

- steigt `ki.aehnliche_faelle` (wenn passende Revisionen existieren),
- ändert sich `ki.kalibrierung.kalibrierungsfaktor` nach NB-Feedback,
- `ki.feedback_loop.status` wechselt ab 5 bzw. 20 Samples,
- Anomalie-Hinweise können erscheinen, wenn NB-Feedback vom aktuellen Fazit abweicht.

**Kein separater Deploy-Schritt** – Logik liegt im Backend-Code, Daten in PostgreSQL.

---

## 5. Datenbank & Export

**Tabelle:** `ki_feedback_records`  
**Spalten:** `feedback_nummer`, `uuid`, `timestamp`, `schema_version`, `previous_hash`, `hash`, `actor_user_id`, `revision_hash`, `data_json`

**Export (manuell, z. B. für Auswertung):**

```sql
SELECT feedback_nummer, timestamp, revision_hash, data_json, hash
FROM ki_feedback_records
ORDER BY feedback_nummer;
```

Ein dediziertes Export-Skript oder CSV-CLI ist **noch nicht** im Repo implementiert.

**Legacy-Datei:** `backend/daten/ki_lerndaten.json` – nur Fallback; für echtes „Lernen“ Revisionen + NB-Feedback in Postgres bevorzugen.

---

## 6. Umgebungsvariablen

Es gibt **keine** KI-spezifischen ENV-Keys (kein `OPENAI_API_KEY` o. Ä.).

Benötigt werden dieselben Pflichtvariablen wie für das Backend allgemein (`DATABASE_URL`, `JWT_*`, `CORS_ORIGINS`, …) – siehe `backend/.env.example` und `.cursor/rules/04-deployment.mdc`.

Frontend: normale Session (`Bearer` + CSRF-Cookie) für `POST /api/v1/ki/feedback` über Proxy `/api/backend/api/v1/ki/...`.

---

## 7. Tests (Referenz)

```bash
cd backend
pytest tests/test_v1_ki_feedback.py -q
pytest tests/test_analyze_v2_route.py::test_analyze_v2_route_exposes_learning_profile -q
```

---

## 8. Roadmap – falls echtes ML gewünscht ist (noch nicht umgesetzt)

Minimal und regelkonform vorgeschlagen:

| Phase | Inhalt | Abhängigkeit |
|-------|--------|--------------|
| **1** | Export-Pipeline (`ki_feedback` + Revision-Features → anonymisiertes Dataset) | ≥ 50–100 verknüpfte Fälle |
| **2** | Offline-Evaluation (Kalibrierung A/B/C, Brier-Score) – **ohne** Live-Änderung der Engine | Datenqualität |
| **3** | Optional: separates Modell nur für **Ranking/Hinweise**, hinter Feature-Flag; Norm-Engine unverändert | Freigabe + ADR in `DECISIONS.md` |
| **4** | Governance: Modellversion in Audit-Log, kein stilles Überschreiben historischer Berechnungen | Revisionssicherheit |

Bis Phase 1 existiert: **operatives Training = Analysen + NB-Feedback sammeln**, nicht GPU-Training.

---

## 9. Häufige Missverständnisse

| Frage | Antwort |
|-------|---------|
| „Muss ich ein Modell hochladen?“ | Nein. |
| „Reicht `ki_lerndaten.json` bearbeiten?“ | Nur Demo/Fallback; Produktion: Revisionen + API-Feedback. |
| „Wann ist es ‚trainiert‘?“ | Pragmatisch: `lernstatus.status` = `LEARNING`/`MATURE` und stabile Kalibrierung über viele verknüpfte Fälle – nicht ein ML-Checkpoint. |
| „Ändert Feedback die Berechnung?“ | Nein, nur KI-Konfidenz/Hinweise/Kalibrierungsfaktor in der KI-Schicht. |

---

## 10. Relevante Dateien (Schnellnavigation)

- `backend/engine/ki_modul.py` – Ähnlichkeit, Konfidenz, Anomalie
- `backend/engine/ki_feedback.py` – Speicherung, Kalibrierung, Lernstatus, Integrität
- `backend/api/v1_ki_feedback.py` – REST
- `backend/services/ki_feedback_service.py` – AuthZ, Audit-Revision
- `frontend/lib/api/ki.ts` – `submitKiFeedback`
- `docs/RISIKO_STATUS.md` – Risiko R-07
