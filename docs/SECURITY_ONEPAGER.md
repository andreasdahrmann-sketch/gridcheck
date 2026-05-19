# GridCheck — Security Onepager

> **Technische Kurzübersicht** für Procurement, IT und Datenschutz. Keine Rechtsberatung.  
> AVV-Entwurf: [AVV_ENTWURF.md](./AVV_ENTWURF.md) · Pentest-Checkliste: [SECURITY_PENTEST_CHECKLIST.md](./SECURITY_PENTEST_CHECKLIST.md)

**Stand:** Mai 2026 · **Abgleich Codebase:** FastAPI-Backend (`backend/main.py`, `backend/core/auth.py`), Next.js-Frontend auf Vercel

---

## Produkt & fachliche Grenze

- **Vorläufige** Netzanschluss-Diagnostik (SaaS) — keine verbindliche Netzanschlusszusage
- **Keine** Behauptung freier Netzkapazität ohne verifizierte Netzbetreiberdaten
- N-1-Screening ohne DSO-Daten: maximal heuristisch (N1-1 / N1-2)

---

## Architektur & Datenresidenz

| Komponente | Hosting | Daten |
|------------|---------|-------|
| **Frontend** | Vercel (Region EU empfohlen) | Keine persistente Kundendatenbank; Session-Cookies über API |
| **API** | Railway (Region EU) | PostgreSQL 16 (+ PostGIS), Berechnungs- und Audit-Daten |
| **Zahlungen** | Stripe (PCI-DSS) | Keine Kartendaten in GridCheck-DB |

**Datenfluss:** Browser → `app.gridcheck.de` → HTTPS → `api.gridcheck.de` → PostgreSQL (Railway).

---

## Authentifizierung & Zugriff

| Maßnahme | Umsetzung (verifiziert) |
|----------|-------------------------|
| **Access-Token** | JWT (HS256), TTL **60 Min** (`backend/services/auth_service.py`) |
| **Refresh-Token** | JWT, TTL **7 Tage**, HttpOnly-Cookie (`gridcheck_refresh`) |
| **Passwörter** | **bcrypt**, 12 Rounds; Policy: min. **12** Zeichen, Groß/Klein, Ziffer, Sonderzeichen |
| **CSRF** | Pflicht auf cookie-basierten Schreib-Endpoints (`X-CSRF-Token` + CSRF-Cookie) |
| **Rate-Limits** | Auth (Register/Login): **10 / 5 Min** pro E-Mail; Analyse/Report-Export scoped (IP/User) |
| **Host-Schutz** | `TrustedHostMiddleware` — `TRUSTED_HOSTS` in Prod setzen |
| **CORS** | Explizite Origins (`CORS_ORIGINS`) + optional Regex für Vercel-Previews |
| **Admin-Registrierung** | Öffentlich **gesperrt** (403) |

Fehlende JWT-Secrets in Prod → Login/Token **503** (fail-fast, kein unsicherer Fallback).

---

## Daten, Revision & Löschung

- **Berechnungen:** Input/Output, Engine-Version, Norm-Version, SHA256-Hash-Kette (`revision_records`, `report_revision_records`, `ki_feedback_records`)
- **Append-only:** historische Berechnungen werden nicht still überschrieben — neue Version bei neuer Datenlage
- **Soft-Delete:** `deleted_at` auf relevanten Entitäten — Daten für Audit erhalten
- **Sicherheits-Logging:** strukturierte Events (`log_security_event`) für Auth, Rate-Limits, Admin-Ablehnungen

---

## Verschlüsselung & Transport

| Ebene | Maßnahme |
|-------|----------|
| **Transit** | HTTPS (TLS) Vercel ↔ Client, Client ↔ Railway |
| **Ruhend** | PostgreSQL bei Railway (Plattform-Verschlüsselung); keine eigenen Karten-/PAN-Daten |
| **Secrets** | Ausschließlich **ENV** (Railway/Vercel), nicht im Git; `JWT_SECRET` / `JWT_REFRESH_SECRET` rotierbar |
| **Stripe** | Nur serverseitige Keys (`sk_*`); Webhook-Secret validiert |

---

## Security-Header (API)

Middleware in `backend/main.py` setzt u. a.:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` (restriktiv für API-Responses)
- `Permissions-Policy` (Geolocation eingeschränkt)

**HSTS:** wird von Vercel/Railway am TLS-Edge bereitgestellt; API setzt kein separates `Strict-Transport-Security` (Edge-Terminierung).

---

## Organisation & Mandantentrennung

- Projekte und Berechnungen an **Benutzer/Organisation** gebunden (BOLA-Vermeidung in API-Services)
- Rollen: u. a. `projektierer`, `netzbetreiber`, `endkunde` — keine Privilegien-Eskalation per Self-Service

---

## Backups & Verfügbarkeit

- **PostgreSQL:** tägliche Railway-Backups (Plattform); Offsite-Backup als Betriebsaufgabe dokumentieren
- **Migrationen:** ausschließlich **Alembic** — kein `AUTO_CREATE_SCHEMA` in Prod
- **Health:** `GET /health` — Status und DB-Check (bei `APP_ENV=prod`)

---

## Incident & Security-Kontakt

| Kanal | Adresse |
|-------|---------|
| **Security / Vorfälle** | security@gridcheck.de *(Platzhalter — produktive Mailbox einrichten und hier pflegen)* |
| **Allgemein / Support** | kontakt@gridcheck.de |

**Meldeinhalt:** Zeitpunkt, betroffene URLs, Request-ID falls vorhanden, keine Passwörter/Token im Klartext.

---

## Offene Punkte (transparent)

- [ ] Externer **Penetrationstest** vor Enterprise-Vertrag — [SECURITY_PENTEST_CHECKLIST.md](./SECURITY_PENTEST_CHECKLIST.md)
- [ ] Formales **ISMS / SOC 2** — derzeit nicht vorhanden
- [ ] **AVV** final durch Rechtsanwalt ([AVV_ENTWURF.md](./AVV_ENTWURF.md))
- [ ] **DPIA** bei personenbezogenen Standort-/Anschlussnehmerdaten (Kunde als Verantwortlicher)
- [ ] Optional: dediziertes **Redis** für verteiltes Rate-Limiting (`REDIS_URL`) — Fallback In-Memory

---

## Schnellreferenz ENV (Prod)

**Railway (API):**

```env
JWT_SECRET=<32+ Zeichen>
JWT_REFRESH_SECRET=<32+ Zeichen, anders>
CORS_ORIGINS=https://app.gridcheck.de
TRUSTED_HOSTS=api.gridcheck.de,app.gridcheck.de,*.up.railway.app
```

**Vercel (Frontend):**

```env
BACKEND_URL=https://api.gridcheck.de
```

DNS-Schritte: [DNS_SETUP.md](./DNS_SETUP.md)

---

*Dieses Dokument ersetzt keine individuelle Sicherheits- oder Datenschutz-Folgenabschätzung.*
