# Legal-Briefing — Index

> **Status: ENTWURF — Stand 2026-06-14.**
> Saemtliche Dokumente sind Entwuerfe, technisch plausibilisiert, **nicht juristisch geprueft**.
> Vor Live-Schaltung: anwaltliche Pruefung gemaess `ANWALT_BRIEFING.md`.

| # | Dokument | Zweck |
|---|----------|-------|
| 1 | [ANWALT_BRIEFING.md](./ANWALT_BRIEFING.md) | Briefing-Paket fuer den Anwalt — Kontext, Liefer-Set, Pruef-Fragen, Timing |
| 2 | [AVV_ENTWURF_v2.md](./AVV_ENTWURF_v2.md) | AVV-Vertragsentwurf nach Art. 28 DSGVO (Modul Auftragsverarbeitung) |
| 3 | [DATENFLUSS_DIAGRAMM.md](./DATENFLUSS_DIAGRAMM.md) | Mermaid-Diagramm + Detail je Datenpfad |
| 4 | [AUFTRAGSVERARBEITER.md](./AUFTRAGSVERARBEITER.md) | Sub-AV-Liste (synchron zu `frontend/lib/legal.ts`) |
| 5 | [TECH_STACK_FUER_ANWALT.md](./TECH_STACK_FUER_ANWALT.md) | 1-Seiten-Onepager: Tech-Stack, Verschluesselung, Compliance-Bezuege |

## Querverweise

- Technische Single Source of Truth: `frontend/lib/legal.ts` (`LEGAL_DATA`, `DATA_PROCESSORS`, `AUFSICHTSBEHOERDEN_BY_BUNDESLAND`, `renderLegalText`, `resolveAufsichtsbehoerde`).
- Architekturentscheidungen: `DECISIONS.md` (insb. ADR-005, ADR-007-DETAIL, ADR-008, ADR-010).
- Compliance-Audit (intern): `docs/COMPLIANCE_AUDIT.md`.
- Bestehender AVV-Stand v1: `docs/AVV_ENTWURF.md` (kuerzere Vorform).
