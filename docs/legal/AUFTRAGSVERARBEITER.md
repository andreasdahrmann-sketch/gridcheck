# Auftragsverarbeiter-Liste

> **Status: ENTWURF — Stand 2026-06-14.**
> Diese Liste ist die menschenlesbare Spiegelung der Konstante `DATA_PROCESSORS` in `frontend/lib/legal.ts`.
> Bei jeder Aenderung an `DATA_PROCESSORS` muss diese Datei aktualisiert werden (oder umgekehrt).
> Single Source of Truth: `frontend/lib/legal.ts`.

---

## Aktive Auftragsverarbeiter / Empfaenger

| Anbieter | Zweck | Sitz / Region | Rechtsgrundlage Art. 6 DSGVO | AVV-Status | Transfergrundlage | Aktiv |
|----------|-------|---------------|------------------------------|------------|-------------------|-------|
| Railway Corp. | Hosting Backend-API + verwaltete PostgreSQL/PostGIS-Instanz | EU-Region (z. B. Frankfurt/Amsterdam) | Art. 6 Abs. 1 lit. b DSGVO i.V.m. Art. 28 DSGVO | abgeschlossen | EU/EWR | ja |
| Vercel Inc. | Hosting Frontend (Next.js), Edge-CDN, Build-Pipeline | USA (EU-Edges bevorzugt) | Art. 6 Abs. 1 lit. b DSGVO i.V.m. Art. 28 DSGVO; Art. 46 DSGVO (SCC) + EU-US Data Privacy Framework | abgeschlossen | SCC + DPF | ja |
| OpenStreetMap Foundation / Nominatim | Geocoding (Adresse zu Koordinaten) und Reverse-Geocoding | EU/UK (gemeinnuetzige Stiftung) | Art. 6 Abs. 1 lit. b bzw. lit. f DSGVO | nicht abgeschlossen (oeffentliche Schnittstelle, fair-use Policy) | EU/EWR (UK mit Angemessenheitsbeschluss) | ja |

## Optional / inaktiv (`active: false`)

> Diese Anbieter sind im aktuellen Live-Build **nicht** aktiv. Vor Aktivierung: anwaltliche Pruefung, Update der Datenschutzerklaerung, ggf. Consent-Banner-Anpassung.

| Anbieter | Zweck | Sitz / Region | Rechtsgrundlage Art. 6 DSGVO | AVV-Status | Transfergrundlage | Aktiv |
|----------|-------|---------------|------------------------------|------------|-------------------|-------|
| Stripe Payments Europe Ltd. / Stripe Inc. | Zahlungsabwicklung (Checkout, Abonnements, Rechnungsverwaltung) | Irland (EU) + USA | Art. 6 Abs. 1 lit. b DSGVO; Art. 46 DSGVO (SCC) + EU-US DPF | abgeschlossen (vorbereitet) | SCC + DPF | nein |
| Sentry (Functional Software, Inc.) | Fehler- und Performance-Monitoring | USA (EU-Region waehlbar) | Art. 6 Abs. 1 lit. f DSGVO bzw. Einwilligung | abgeschlossen (vorbereitet) | SCC + DPF | nein |

---

## Pflicht-Hinweise

- **Sub-AV-Wechsel:** geplante Aenderungen werden mit Vorlauf textlich angezeigt. Widerspruchsrecht des Verantwortlichen siehe AVV § 7.
- **Drittlandtransfers:** sofern verarbeitet wird ausserhalb EU/EWR (Vercel, optional Stripe / Sentry), erfolgt dies ausschliesslich auf Basis der **Standardvertragsklauseln (Art. 46 DSGVO)** in Verbindung mit dem **EU-US Data Privacy Framework**.
- **Erweiterungs-Regel:** Diese Liste darf NICHT mit erfundenen Anbietern erweitert werden. Jeder Eintrag braucht einen real abgeschlossenen AVV oder vergleichbaren Vertrag (Cursor-Rule, Datenquellenregel).
- **Aufsicht:** Zustaendige Datenschutz-Aufsichtsbehoerde wird aus dem Sitz-Bundesland des Verantwortlichen aufgeloest (`AUFSICHTSBEHOERDEN_BY_BUNDESLAND` in `frontend/lib/legal.ts`).
