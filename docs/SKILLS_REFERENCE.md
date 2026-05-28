---
source: Skills.docx (vom Nutzer geliefert)
imported: 2026-05-24
status: Leitfaden für Skill-Auswahl, MVP-Roadmap und Architektur-Entscheidungen
---

# Skills-Referenz – Pre-Netzanschluss-Check-App

> **Hinweis zur Übernahme in GridCheck:** Dieser Leitfaden nennt Drizzle/Supabase/Next-15-Architektur. Der GridCheck-Stack ist abweichend (Next.js 14 + FastAPI Python + PostgreSQL/Alembic + Railway/Vercel). Die *Prinzipien* (Snapshot-Revision, Validierung im Backend, Auth, Reviews, KI später) gelten 1:1; die *konkreten Werkzeuge* werden auf den vorhandenen Stack gemappt (siehe `DECISIONS.md`, `docs/PROJEKTIERER_ARCHITECTURE.md`, `docs/COMPLIANCE_AUDIT.md`).

## 1. Ziel

Pre-Netzanschluss-Check-App als Diagnosewerkzeug mit:

- schneller Ersteinschätzung
- nachvollziehbaren Ergebnissen
- strukturierter Diagnose statt Ja/Nein
- Empfehlungen für nächste Schritte
- revisionssicherer Speicherung
- Erweiterbarkeit (N-1, Netzplan, KI)

## 2. Skill-Bereiche

1. Backend / API
2. Authentifizierung und Benutzerverwaltung
3. Datenbank und Persistenz
4. Validierung
5. Frontend / UX / UI
6. Sicherheit / Reviews
7. Erweiterungen und Skalierung

## 3. Skill-Einsatz-Tabelle (gekürzt)

| Bereich | Skill | Wann | Nutzen |
|---|---|---|---|
| Backend / API | api-design-principles | Anfang | klare Endpunktstruktur |
| Backend / API | api-design-patterns | Anfang | Erweiterbarkeit, Versionierung |
| Backend / API | api-security-best-practices | API-Design | Schutz Tokens/Sessions/Errors |
| Auth | better-auth-* | bei Login/Rechten | Rollen, Sessions, Mandanten |
| DB | postgresql-table-design | vor Implementierung | Revisionssicherheit, Snapshots |
| DB | drizzle-orm → SQLAlchemy/Alembic | Bauphase | typsicher, GridCheck nutzt Alembic |
| DB | drizzle-migrations → alembic | ab erster DB-Version | Schema-Versionierung |
| Validierung | zod (Frontend) + Pydantic (Backend) | sofort | Eingabe-/Payload-Schutz |
| Frontend | frontend-design | früh | klare Nutzerführung |
| Frontend | web-design-guidelines | früh + laufend | Bedienbarkeit, Vertrauen |
| Frontend | shadcn-ui | Aufbau Frontend | UI-Bausteine |
| Sicherheit | security-best-practices | dauerhaft | Pflicht für B2B |
| Review | security-review | vor Pilot/Live | Schwachstellen erkennen |
| Review | api-security-review | wenn APIs stehen | Auth/Rate-Limit/Error-Sicherheit |
| Review | postgresql-code-review | wenn DB-Logik existiert | Indizes, Constraints |
| Skalierung | bff-api | komplexes Frontend | UI-spezifische Aggregation |
| Skalierung | postgresql-optimization | bei Wachstum | Performance |
| KI | ai-sdk | nach stabilem Kern | Empfehlungen, Lernfälle |

## 4. Zentrale Prinzipien (für GridCheck verbindlich)

### Revisionssicherheit als Datenmodell, nicht nur PDF
Jede Berechnung basiert auf einem **Snapshot** mit:
- Eingabedaten
- Modellversion
- Regelwerksstand
- Annahmen
- Ergebnisse
- Zeitstempel
- Benutzer / Auslöser

PDF und Anzeige werden **aus diesem Snapshot abgeleitet** – nicht umgekehrt.

GridCheck-Mapping: `analysis_runs`, `gridcheck_result_audit`, `revision_chain` (siehe Migrationen `20260507_*`, `20260512_03`).

### Kein KI-Fokus zu früh
Reihenfolge: Datenmodell → Fachlogik → API → Validierung → Auth → Frontend → Reviews → erst dann KI.

### Validierung beidseitig
Frontend `zod` und Backend `Pydantic` müssen unabhängig validieren – Frontend-Validierung allein reicht nie.

### Diagnose statt Ampel
Ergebnis enthält:
- voraussichtliche Anschlussfähigkeit (A/B/C – nicht nur grün/rot)
- kritische Engpassfaktoren
- Unsicherheiten / Confidence
- empfohlene nächste Schritte
- Variantenvergleich
- Hinweis auf zusätzliche Prüfungen
- Export / Bericht / Audit-Nachweis

## 5. Priorisierung (Kurzform)

**Früh / Fundament**: postgresql-table-design, api-design-principles/patterns, zod, security-best-practices, frontend-design, web-design-guidelines.

**Bauphase**: drizzle-orm/migrations (→ SQLAlchemy/Alembic in GridCheck), better-auth-* (→ JWT + bcrypt + CSRF), api-security-best-practices, shadcn-ui.

**Vor Pilot**: security-review, api-security-review, postgresql-code-review.

**Wachstum**: bff-api, postgresql-optimization, ai-sdk.

## 6. MVP-Roadmap (Phasen)

- **Phase 0** Zielbild + Fachlogik
- **Phase 1** Datenmodell
- **Phase 2** DB technisch (Alembic)
- **Phase 3** Minimal-API
- **Phase 4** Validierung + Sicherheit
- **Phase 5** Auth + Zugriffsschutz
- **Phase 6** Frontend MVP
- **Phase 7** Reviews / Härtung
- **Phase 8** BFF / Optimierung / KI

## 7. Typische Fehler (vermeiden)

1. zu früher KI-Start
2. unsaubere Datenmodellierung → Revisionssicherheit nicht nachrüstbar
3. nur Frontend-Validierung
4. chaotische API
5. Sicherheit erst am Ende
6. überladene Oberfläche
7. PDF-Fokus statt Snapshot-Fokus
8. fehlende Rollen-/Rechteplanung

## 8. Architektur-Skizze des Nutzers (Hinweis)

Der Nutzer hat eine Skizze mit Next.js 15 / React 19 / Supabase übermittelt. **Abgleich mit GridCheck-Realität:**

| Skizze | GridCheck-Stack |
|---|---|
| Next.js 15 / React 19 | Next.js 14 + React 18 (kein Upgrade ohne Plan) |
| Tailwind | ✅ vorhanden |
| TanStack Query | ✅ vorhanden |
| Zustand | teilweise (Context + Hooks); kein separater Store-Layer |
| Supabase Auth/DB/Storage/Realtime | ❌ FastAPI + PostgreSQL (Railway) + JWT + ReportLab; kein Realtime |

→ Umstellung auf Supabase wäre ein kompletter Stack-Wechsel und wird **nicht** ohne ADR durchgeführt.

## 9. Painpoint Netzbetreiber – Soll-Flow des Nutzers

```
1. Projektierer gibt Anlage ein (Standort, Leistung, Typ)
2. App: "Gibt es bereits eine Netzanfrage in diesem Bereich?" (Kumulations-Check)
3. NB sieht in seinem Dashboard alle offenen Anfragen georeferenziert
4. Vorprüfung mit echten Netzdaten → Antwort in Stunden statt Wochen
5. Digitale Einspeisezusage mit Auflagen
```

GridCheck-Status (Mai 2026):

- (1) Wizard inkl. Anlagentyp/AC/DC vorhanden ✅
- (2) `coincidence_factor_screening` warnt qualitativ, **echte Kumulation pro NB-Region/Trafo fehlt** ❌
- (3) NB-Dashboard existiert (gated), aber **kein georeferenzierter Cross-Project-View** ❌
- (4) Vorprüfung mit Engine v2 läuft, **echte Netzdaten / DSO-Schnittstelle fehlt** ❌
- (5) Digitale Auflagen im PDF, **„Einspeisezusage" als formales Dokument fehlt** ❌

Backlog-Aufgaben dazu in `docs/ROADMAP_BACKLOG.md` ergänzen, ADR notwendig für (2)-(4).
