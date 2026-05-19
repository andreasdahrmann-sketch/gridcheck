# GridCheck Compliance-Audit

**Datum:** 2026-05-19  
**Scope:** Cursor Rules (`00-gridcheck`, `03-elektrotechnik`, `05-workflow`, `06-arbeitsweise`, `08-decisions-binding`), `DECISIONS.md` (ADR-005, 008–010), DE/EU-Normen (high level), Revisionssicherheit, Security, Frontend-Consumer, Marketing-Claims, VNB-Zugang  
**Methodik:** Statischer Code-Review, Spot-Checks in Tests (`test_n1_analyse`, `test_vnb_access_control`, `test_auth_projects_api`), keine Rechtsberatung.

## Executive Summary

| Gesamturteil | **Teilweise compliant** |
|--------------|-------------------------|
| Go-Live Kernpfad | Tragfähig (Engine, Audit-Chain, PDF, Auth/BOLA, VNB-Gates) |
| Blocker Prod | Impressum (Nutzer), `NORM_VERSION`/`APP_VERSION` ENV, Consent vor optionalem Tracking |

**Top-Lücken (priorisiert):**

1. **Impressum** fehlt bewusst (Nutzer-Aufgabe).
2. **`NORM_VERSION` ENV** in Railway noch setzen (`04-deployment.mdc`; Registry bleibt Code-SSoT).
3. **Consent-Banner** nur Hinweis – vor Sentry/Analytics erweitern.
4. **Datenschutz** = Grundgerüst mit Platzhalter – vor Live mit AV-Verzeichnis abstimmen.

---

## Checkliste (PASS / WARN / FAIL)

| Bereich | Kriterium | Status | Befund |
|--------|-----------|--------|--------|
| **Elektrotechnik** | Keine behauptete freie Netzkapazität ohne VNB-Beleg | **PASS** | Engine/OSM-Disclaimer; `nvp_freie_kapazitaet_kw` nur Nutzer-/VNB-Eingabe; UI-Hinweis am Kapazitätsfeld |
| **Elektrotechnik** | N-1 max. N1-2 ohne DSO (`06-arbeitsweise`) | **PASS** | `n1_analyse.klassifiziere_n1_klasse` cappt N1-3/4 → N1-2; DSO-verifiziert erlaubt N1-4 |
| **Elektrotechnik** | Normversion bei Berechnung | **PASS** | `norm_version` + `norm_registry_stand` in `berechne_netzanschluss`; `gridcheck_result_audit.norm_version` |
| **Elektrotechnik** | Annahmen + Confidence in Ergebnis | **PASS** | `transparenz`, `n1_mvp_dokumentation`, `datenqualitaet` |
| **Elektrotechnik** | Konservatives Runden / kein Sk''-Schätzen als verbindlich | **PASS** | Vorläufig-Vermerke; UI-Ik-Bänder nur Hinweis (`gridcheck-engine.ts`) |
| **Revisionssicherheit** | Input/Output/Norm/App/User/Zeit | **PASS** | `analysis_runs`, `revision_records`, `gridcheck_result_audit` |
| **Revisionssicherheit** | Append-only, kein stiller Overwrite | **PASS** | Neue Runs/Revisionsnummern; Ergebnisse nicht per UPDATE überschrieben |
| **Revisionssicherheit** | PDF: Audit-Hash + Disclaimer | **PASS** | `pdf_builder.py` Engine-Revision, Source-Checksums, Footer-Disclaimer |
| **Revisionssicherheit** | Soft-Delete | **PASS** | `projects.deleted_at` |
| **GDPR** | Datenschutzseite | **WARN** | `/datenschutz` mit Grundgerüst + `PlaceholderNotice`; Impressum offen |
| **GDPR** | Kein unnötiges PII-Logging | **PASS** | Strukturiertes Logging; Passwörter nicht geloggt |
| **GDPR** | Cookie-Hinweis | **WARN** | `CookieNotice` – technisch notwendig; Analytics „derzeit nicht aktiv“ |
| **GDPR** | Datenquellen-Attribution | **PASS** | Data-Source-Modelle; OSM-Disclaimer in API/Engine |
| **Security** | JWT, CORS, Rate-Limits | **PASS** | `core/config`, `core/rate_limit`, Auth/Analyze-Tests |
| **Security** | BOLA Projekte | **PASS** | `project_service` Owner/Member; geschützte Projekt-Reads/Writes |
| **Security** | VNB-Dashboard + Kommunikation | **PASS** | `vnb_verification_status`; `require_verified_netzbetreiber`; Frontend `ProtectedVnbRoute` / `VnbVerifiedRoute`; Tests `test_vnb_access_control` |
| **Security** | Keine Secrets im Code | **PASS** | `pydantic-settings` / ENV fail-fast in Prod |
| **Frontend** | Kein Scoring in Frontend | **PASS** | `analyze.ts` mappt API; `gridcheck-engine.ts` nur UI-Hinweise (Ik-Band, Leistungsrichtwerte) |
| **Frontend** | Verdict mit Begründung | **PASS** | Fazit, Transparenz, N-1-Texte, `AnalysisDisclaimer` |
| **App-Claims** | Landing ohne unbewiesene Genauigkeit | **PASS** | „keine garantierte Prognosegenauigkeit“ (`app/page.tsx`) |
| **App-Claims** | Disclaimer sichtbar | **PASS** | Footer, Ergebnisblöcke, VNB-Seite konservativ formuliert |

---

## Detail: VNB-Zugang (2026-05-19)

| Schicht | Mechanismus |
|---------|-------------|
| DB | `users.vnb_verification_status` (`none` / `pending` / `approved`), Migration `20260519_02` |
| API | `core/vnb_access.py`, Stakeholder `/netzbetreiber` mit `require_vnb_verification=True`, `/api/v1/vnb/comms/*` mit `require_verified_netzbetreiber` |
| Frontend | `/vnb` → `ProtectedVnbRoute`; `/vnb/kommunikation` → `VnbVerifiedRoute` |
| Admin | `scripts/approve_netzbetreiber.py` |

Siehe auch `docs/VNB_ACCESS.md`.

---

## In diesem Lauf behoben (kritisch / klar)

| # | Problem | Fix |
|---|---------|-----|
| 1 | `gridcheck_result_audit` wurde nicht befüllt | `_persist_gridcheck_result_audit` in `persist_completed_analysis_run` |
| 2 | Normversion fehlte im Engine-Result | `norm_version` / `norm_registry_stand` in `berechne_netzanschluss` |
| 3 | Revision ohne Nutzer/Projekt-Kontext | `revision_context` im Analyze-V2-Pfad |
| 4 | UI widersprach N-1-Regel (N1-3 ohne DSO) | `ProjectProfileFields` → maximal **N1-2** |
| 5 | VNB-Zugang ohne Verifizierung | `vnb_verification_status` + Gates Backend/Frontend + Tests |
| 6 | Formular „Freie Kapazität“ ohne Kontext | Label „VNB-Kapazitätsangabe“ + Hinweistext |

---

## Verifikation (Auszug)

```powershell
cd backend
python -m pytest tests/test_n1_analyse.py tests/test_vnb_access_control.py -q --tb=no
```

Erwartung: grün (PostgreSQL-Test-DB gemäß `conftest.py`).

---

## Verbleibende Nutzer-/Projekt-Aktionen

1. **Impressum** legal fertigstellen (bewusst aus Scope dieses Laufs).
2. **`NORM_VERSION` ENV** in Railway setzen (`04-deployment.mdc`).
3. **Consent-Banner** vor optionalem Analytics/Sentry erweitern (Opt-in).
4. **Produktiv:** `APP_VERSION` aus Git-Tag injizieren.
5. **Datenschutz** mit Verarbeitungsverzeichnis/AV-Verträgen finalisieren.
6. **Regelmäßiger Audit-Lauf** nach größeren Engine-/N-1-/VNB-Änderungen.

---

## Referenzen

- `DECISIONS.md` — ADR-005 (Hash-Chain), ADR-008–010 (PostgreSQL, Alembic)
- `.cursor/rules/03-elektrotechnik.mdc`, `06-arbeitsweise-gridcheck.mdc`, `08-decisions-binding.mdc`
- `backend/compliance/norm_registry.py`
- `backend/engine/n1_analyse.py` (N1-Cap, ca. Zeilen 658–660)
- `backend/services/billing_service.py` (`_persist_gridcheck_result_audit`)
- `backend/core/vnb_access.py`
