# Technologie-Stack — Onepager fuer den Anwalt

> Stand: 2026-06-14. Quelle: `DECISIONS.md` (ADR-004, ADR-007-DETAIL, ADR-008–010), `docs/COMPLIANCE_AUDIT.md`, `frontend/package.json`, `backend/requirements.txt`.
> Zweck: Schneller Ueberblick fuer juristische Pruefung von DSGVO/AVV/Drittlandtransfers.

---

## 1. Backend

- **Sprache / Framework:** Python 3.11+, FastAPI
- **Datenbank:** PostgreSQL 16 mit PostGIS (geo-faehig)
- **ORM / Migration:** SQLAlchemy 2.x, Alembic (versionierte Migrationen, ADR-010)
- **Auth:** JWT (kurzlebiger Access-Token + Refresh-Token), `bcrypt` Passwort-Hash
- **Validierung:** Pydantic v2
- **Logging:** strukturiertes JSON-Logging (`structlog`), keine PII-Logs in Klartext
- **Audit:** Append-only Audit-Tables + SHA256 Hash-Chain (ADR-005), revisionssicher
- **Hosting:** Railway (EU-Region), verwaltete Postgres-Instanz, taegliche Backups (Railway-Automatik)
- **Sicherheit:** TLS, CORS-Whitelist, Rate-Limiting, BOLA-Schutz auf Projektressourcen, Secrets ausschliesslich ueber ENV (kein Klartext im Code), Healthcheck-Endpoint
- **Optional:** Sentry (Error-Monitoring) — derzeit inaktiv, vorbereitet

## 2. Frontend

- **Framework:** Next.js 14 (App Router), React 18, TypeScript strict
- **Styling:** TailwindCSS, shadcn/ui-Komponenten
- **Forms / Validation:** React Hook Form + Zod
- **Datenflow:** `@tanstack/react-query`, kein Redux, kein eigenes globales Caching
- **Karten:** Leaflet / react-leaflet (OpenStreetMap-Tiles)
- **Hosting:** Vercel (Edges, EU-Region bevorzugt), Static- + Server-Components
- **Native (geplant / optional):** Capacitor 8.3.x fuer Android/iOS-Wrapper

## 3. Datenfluesse / Drittlandtransfers

| Datenstrom | Region | Transfergrundlage |
|------------|--------|-------------------|
| Browser <-> Vercel | weltweit (EU bevorzugt) | EU/USA, SCC + EU-US DPF |
| Vercel <-> Railway-Backend | EU | EU/EWR |
| Backend <-> PostgreSQL/PostGIS | EU (Railway) | EU/EWR |
| Backend <-> Nominatim (OSM) | EU/UK | EU/EWR (UK mit Angemessenheitsbeschluss) |
| Backend <-> Sentry (optional) | USA (EU waehlbar) | SCC + EU-US DPF |
| Backend <-> Stripe (optional) | IE/USA | SCC + EU-US DPF |

Detail siehe `DATENFLUSS_DIAGRAMM.md`.

## 4. Verschluesselung

- **Transport:** TLS 1.2+ ueberall (Browser, Vercel-Edge, Railway-Backend, DB-Verbindung, externe APIs)
- **At rest:** Plattform-Standardverschluesselung (Railway-managed Volumes / DB)
- **Passwoerter:** bcrypt (>= 12 rounds, ADR-konform)

## 5. Kein Tracking / kein Vendor-Lock-in

- **Kein Supabase** (ADR-007-DETAIL) — Datenhoheit bleibt bei Railway-EU.
- **Kein nicht-essenzielles Tracking aktiv.** Reichweitenmessung / Marketing-Cookies nur nach Opt-In Cookie-Banner; im Live-Build derzeit nicht aktiv.
- **Audit-Logs lokal/EU-souveraen.** Kein Cloud-Audit-Service ausserhalb EU.

## 6. Compliance-/Norm-Bezuege

- DSGVO (Verordnung (EU) 2016/679)
- BDSG (insbesondere § 38 — DSB-Bestellpflicht)
- TTDSG / TDDDG — Endgeraete-Zugriff / Cookies
- HGB § 257 / AO § 147 — Aufbewahrungspflichten
- KRITIS / BSI-Naehe (Energiewirtschaft) — App ist ausschliesslich Diagnose-Werkzeug, **keine** Steuerung kritischer Infrastruktur

## 7. Versionierung / Audit-Identifikation

- Jeder Diagnose-Report enthaelt: `app_version`, `norm_version`, `audit_id` (Hash), Zeitstempel — Voraussetzung fuer Revisionssicherheit (ADR-005).

---

> **Hinweis:** Onepager-Verdichtung. Die vollstaendige technische Architektur ist in `DECISIONS.md` und `docs/COMPLIANCE_AUDIT.md` dokumentiert.
