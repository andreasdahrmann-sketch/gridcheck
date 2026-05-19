# VNB-Zugang (Netzbetreiber-Dashboard)

## Ziel

Das Netzbetreiber-Dashboard und alle VNB-spezifischen API-Pfade sind nur fuer **freigeschaltete** Konten mit Rolle `netzbetreiber` erreichbar. Alle anderen Nutzer erhalten HTTP 403 mit Code `VNB_ACCESS_DENIED`.

## Datenmodell

Tabelle `users`, Spalte `vnb_verification_status`:

| Wert | Bedeutung |
|------|-----------|
| `none` | Kein VNB-Freischaltungsprozess (Standard fuer Endkunde/Projektierer) |
| `pending` | Registrierung als Netzbetreiber, Identitaet wird geprueft |
| `approved` | Freigeschaltet — VNB-Dashboard und VNB-APIs erlaubt |

Zusaetzlich liefert `/api/v1/auth/me` das berechnete Feld `netzbetreiber_verified` (`true` nur bei Rolle `netzbetreiber` und Status `approved`).

**Migration:** `20260519_02_vnb_verification_status`

## Registrierung

- Rolle `netzbetreiber` bei `/api/v1/auth/register` setzt automatisch `vnb_verification_status=pending`.
- Zugang zum Dashboard bleibt gesperrt, bis ein Administrator freischaltet.

## Freischaltung (Admin)

### REST (nur Admin, CSRF bei Cookie-Auth)

```http
POST /api/v1/admin/users/{user_id}/approve-netzbetreiber
Authorization: Bearer <admin-access-token>
X-CSRF-Token: <csrf>   # bei Cookie-Session
```

Antwort enthaelt `vnb_verification_status: "approved"` und `netzbetreiber_verified: true`.

### CLI / Skript

```powershell
cd backend
python -m scripts.approve_netzbetreiber --user-id 42
```

Voraussetzung: Benutzer existiert und hat Rolle `netzbetreiber`.

## Geschuetzte Backend-Routen

- `POST /api/v1/stakeholder/netzbetreiber`
- `POST /api/v2/reports/vnb`
- `POST /api/v1/ki/feedback` mit `quelle=netzbetreiber`

Administratoren (`role=admin`) duerfen VNB-Pfade zu Testzwecken nutzen (Bypass).

## Frontend

- Route `/vnb` und Layout `app/vnb/layout.tsx` mit `ProtectedVnbRoute`
- Header-Link „VNB“ nur bei `netzbetreiber_verified`
- Startseite: Tab „Netzbetreiber-Dashboard“ nur fuer freigeschaltete Nutzer

### Nutzertexte (403 / Sperrbildschirm)

| Zustand | Meldung |
|---------|---------|
| Falsche Rolle | Dieses Dashboard ist nur fuer Netzbetreiber. Registrieren Sie sich mit Rolle Netzbetreiber und lassen Sie sich freischalten. |
| `pending` | Ihre Identitaet als Netzbetreiber wird geprueft... |
| Links | Kontakt (`/contact?intent=vnb-pilot`), Einstellungen (`/settings`) |

## Tests

```powershell
cd backend
pytest tests/test_vnb_access_control.py -q
```

## Betrieb

Nach Deploy Migration ausfuehren:

```powershell
cd backend
alembic upgrade head
```

Bestehende Konten mit Rolle `netzbetreiber` werden durch die Migration auf `pending` gesetzt (nicht automatisch freigeschaltet).
