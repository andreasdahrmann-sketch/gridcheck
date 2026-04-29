# GridCheck – UI Guidelines

## Design-Prinzipien
- Klarheit vor Komplexität: Ergebnisse sofort erkennbar
- Fachlich korrekt: Elektrotechnik-Terminologie konsistent
- Revisionssicher: Jede Aktion nachvollziehbar
- Mobil-kompatibel: Responsive ab 375px

## Status-Darstellung (KEIN reines Ampelsystem)

| Status                  | Farbe       | Bedeutung                                     |
|-------------------------|-------------|-----------------------------------------------|
| MACHBAR                 | emerald-600 | Anschluss technisch möglich, keine Maßnahmen  |
| MACHBAR_MIT_AUFLAGEN    | amber-500   | Möglich mit definierten Maßnahmen             |
| GRENZWERTIG             | orange-500  | Technisch möglich, wirtschaftlich kritisch    |
| NICHT_MACHBAR           | destructive | Technisch nicht realisierbar                  |
| DATEN_UNVOLLSTAENDIG    | muted-fg    | Weitere Eingaben erforderlich                 |

Status IMMER mit Diagnose-Text und Empfehlungen kombinieren!

## Netzplan-Farben

| Element          | Farbe   | Bedeutung           |
|------------------|---------|---------------------|
| Leitung normal   | #22c55e | Betrieb OK          |
| Leitung überlast | #ef4444 | Überlastung         |
| Leitung kritisch | #f97316 | > 80% Auslastung    |
| N-1-kritisch     | #a855f7 | Fällt bei N-1 aus   |
| Neuer Anschluss  | #3b82f6 | Geplanter Anschluss |
| Umspannwerk      | #1e293b | HV/MV-Knoten        |

## Komponenten

### Buttons
- variant=default: Hauptaktion (Check starten, Bericht exportieren)
- variant=outline: Sekundäre Aktionen, Filter, Navigation zurück
- variant=ghost: Toolbar-Aktionen, Sidebar-Items
- variant=destructive: Projekt löschen, Check zurücksetzen

### Check-Wizard
- Multi-Step-Form mit validiertem Fortschritt
- Jeder Schritt einzeln speicherbar (kein Datenverlust bei Abbruch)
- Pflichtfelder klar markiert
- Fachbegriffe mit InfoTooltip erklären

### Diagnose-Karte (Kern-Komponente)
- Props: status, title, summary, details, recommendations, n1Result, auditId
- Ergebnis-Detail in Sheet (Seitenblatt, nicht Modal)
- Netzplan in Dialog mit maximierter Ansicht

## Formulare

| Feld                 | Typ    | Einheit | Validierung       |
|----------------------|--------|---------|-------------------|
| Anschlussleistung    | number | kVA     | 1 – 100.000       |
| Spannungsebene       | select | –       | NS/MS/HS/HöS      |
| cos phi              | number | –       | 0.6 – 1.0         |
| Gleichzeitigkeit     | number | –       | 0.1 – 1.0         |
| Anschlussart         | select | –       | Einspeisung/Bezug |

## Loading States

### Berechnungs-Schritte (Check-Wizard)
Schritte: Eingabe → Topologie → Lastfluss → N-1 → KI → Ergebnis
Kein globaler Overlay, nur innerhalb der Check-Card.

## Navigation
- Interne Navigation: next/link (KEIN window.location.href)
- Auth-Gates: Middleware + (protected)/layout.tsx
- Rollen: admin, netzbetreiber, projektierer
