# GridCheck — Security Onepager (Entwurf)

> Keine Rechtsberatung. Fuer Enterprise-Procurement als **technische Kurzuebersicht**. AVV: [AVV_ENTWURF.md](./AVV_ENTWURF.md).

## Produkt

Vorlaeufige Netzanschluss-Diagnostik (SaaS). **Keine** verbindliche Netzanschlusszusage.

## Architektur

| Komponente | Hosting | Daten |
|------------|---------|-------|
| Frontend | Vercel (EU) | Keine DB, Session-Cookies |
| API | Railway (EU) | PostgreSQL, revisionssichere Logs |
| Zahlungen | Stripe (PCI-DSS) | Keine Karten in GridCheck-DB |

## Authentifizierung

- JWT Access (kurz) + Refresh-Token (HttpOnly-Cookie)
- Passwort-Policy (min. 12 Zeichen, Komplexitaet)
- CSRF auf cookie-basierten Schreib-Endpoints
- Rate-Limits auf Auth und Report-Export

## Daten & Revision

- Berechnungen: Input/Output-Hash, Engine-Version, Norm-Version
- Append-only Audit (`revision_records`, `ki_feedback_records`)
- Soft-Delete (`deleted_at`) — keine stillen Ueberschreibungen

## Transport & Headers

- HTTPS (Prod)
- CSP, HSTS, `X-Frame-Options: DENY`, `Referrer-Policy`

## Secrets

- Nur ENV (Railway/Vercel), nicht im Git
- `JWT_SECRET` / `JWT_REFRESH_SECRET` rotierbar
- Stripe nur serverseitig (`sk_*`)

## Offene Punkte (ehrlich)

- [ ] Penetrationstest vor Enterprise-Vertrag
- [ ] Formales ISMS / SOC2 — nicht vorhanden
- [ ] AVV final durch Rechtsanwalt
- [ ] DPIA bei personenbezogenen Projektstandorten

## Kontakt Security

`kontakt@gridcheck.de` (Platzhalter — produktive Adresse pflegen)
