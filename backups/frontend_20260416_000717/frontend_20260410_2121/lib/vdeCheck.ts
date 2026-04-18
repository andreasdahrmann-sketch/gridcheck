// src/lib/vdeCheck.ts
// Pruefung der Anforderungen nach VDE AR-N 4105/4110/4120/4130
// Blindleistung, cos-phi-Vorgaben, Wirkleistungsreduzierung

import type { Spannungsebene } from '@/types';

export type VdeRegelwerk = 'VDE-AR-N 4105' | 'VDE-AR-N 4110' | 'VDE-AR-N 4120' | 'VDE-AR-N 4130';

export interface VdeAnforderung {
  regelwerk: VdeRegelwerk;
  cos_phi_min: number;       // Mindest-cos-phi (induktiv/kapazitiv)
  cos_phi_max: number;       // Max cos-phi (typisch 1.0)
  q_lieferpflicht: boolean;  // Muss Blindleistung liefern koennen?
  q_bereich_pct: number;     // Blindleistungsbereich in % von Sn
  p_reduzierung_fernsteuerbar: boolean;
  zertifikat_erforderlich: boolean;
  einheitenzertifikat: boolean;
  anlagenzertifikat: boolean;
  netzvertraeglichkeit_studie: boolean;
  schutzkonzept_erforderlich: boolean;
  max_anschlussleistung_kw: number | null; // null = unbegrenzt
  bemerkungen: string[];
}

export function getVdeAnforderung(se: Spannungsebene, p_kw: number, isEinspeiser: boolean): VdeAnforderung {
  // Verbraucher haben weniger strenge Anforderungen
  if (!isEinspeiser) {
    return {
      regelwerk: se === 'NS' ? 'VDE-AR-N 4105' : se === 'MS' ? 'VDE-AR-N 4110' : 'VDE-AR-N 4120',
      cos_phi_min: 0.9,
      cos_phi_max: 1.0,
      q_lieferpflicht: false,
      q_bereich_pct: 0,
      p_reduzierung_fernsteuerbar: false,
      zertifikat_erforderlich: false,
      einheitenzertifikat: false,
      anlagenzertifikat: false,
      netzvertraeglichkeit_studie: se === 'HS',
      schutzkonzept_erforderlich: se !== 'NS',
      max_anschlussleistung_kw: null,
      bemerkungen: ['Verbraucheranschluss: Blindleistungskompensation empfohlen bei cos_phi < 0.9'],
    };
  }

  // === Einspeiser ===
  if (se === 'NS') {
    return {
      regelwerk: 'VDE-AR-N 4105',
      cos_phi_min: 0.90,
      cos_phi_max: 1.0,
      q_lieferpflicht: p_kw > 4.6,          // Ab 4.6 kW Blindleistungspflicht
      q_bereich_pct: p_kw > 4.6 ? 10 : 0,   // cos(phi) 0.9 ind bis 0.9 kap
      p_reduzierung_fernsteuerbar: true,       // 70%-Regel bzw. Fernsteuerung
      zertifikat_erforderlich: false,
      einheitenzertifikat: p_kw > 135,         // Ueber 135 kW → Einheitenzertifikat
      anlagenzertifikat: false,
      netzvertraeglichkeit_studie: false,
      schutzkonzept_erforderlich: false,
      max_anschlussleistung_kw: 135,           // Darueber → MS
      bemerkungen: p_kw > 135
        ? ['Leistung > 135 kW: Anschluss an MS-Ebene erforderlich (VDE-AR-N 4110)']
        : p_kw > 30
          ? ['Ab 30 kW: Einspeisemanagement/Fernsteuerbarkeit erforderlich']
          : ['NS-Standardanschluss nach VDE-AR-N 4105'],
    };
  }

  if (se === 'MS') {
    return {
      regelwerk: 'VDE-AR-N 4110',
      cos_phi_min: 0.90,
      cos_phi_max: 1.0,
      q_lieferpflicht: true,
      q_bereich_pct: 32.87,                   // cos(phi) 0.95 ind/kap bei Pn → ~32.87% Qn
      p_reduzierung_fernsteuerbar: true,
      zertifikat_erforderlich: true,
      einheitenzertifikat: true,
      anlagenzertifikat: p_kw > 950,           // Anlagenzertifikat Typ B ab 950 kW
      netzvertraeglichkeit_studie: p_kw > 1000,
      schutzkonzept_erforderlich: true,
      max_anschlussleistung_kw: null,
      bemerkungen: [
        'Einheitenzertifikat erforderlich',
        ...(p_kw > 950 ? ['Anlagenzertifikat Typ B erforderlich (> 950 kW)'] : []),
        ...(p_kw > 1000 ? ['Netzvertraeglichkeitspruefung durch NB erforderlich'] : []),
        'Blindleistung: cos(phi) = 0.95 ind bis 0.95 kap am NAP',
        'Q(U)-Regelung oder cos(phi)(P)-Kennlinie nach NB-Vorgabe',
      ],
    };
  }

  // HS (110 kV+)
  return {
    regelwerk: 'VDE-AR-N 4120',
    cos_phi_min: 0.925,
    cos_phi_max: 1.0,
    q_lieferpflicht: true,
    q_bereich_pct: 39.5,                      // cos(phi) 0.925 → ~39.5% Qn
    p_reduzierung_fernsteuerbar: true,
    zertifikat_erforderlich: true,
    einheitenzertifikat: true,
    anlagenzertifikat: true,
    netzvertraeglichkeit_studie: true,
    schutzkonzept_erforderlich: true,
    max_anschlussleistung_kw: null,
    bemerkungen: [
      'Anlagenzertifikat Typ A2 erforderlich',
      'Dynamische Netzstuetzung (LVRT/HVRT) erforderlich',
      'Blindleistung: cos(phi) = 0.925 ind bis 0.925 kap am NAP',
      'Frequenzabhaengige Wirkleistungsreduzierung (P(f)) erforderlich',
      'Netzvertraeglichkeitspruefung + Netzanschlusszusage erforderlich',
      ...(p_kw > 50000 ? ['Systemrelevante Anlage: Anforderungen nach VDE-AR-N 4130 pruefen'] : []),
    ],
  };
}

export interface VdePruefResult {
  regelwerk: VdeRegelwerk;
  anforderung: VdeAnforderung;
  cos_phi_ok: boolean;
  cos_phi_eingabe: number;
  hinweise: string[];
  warnungen: string[];
}

export function pruefeVdeKonformitaet(
  se: Spannungsebene, p_kw: number, cos_phi: number, isEinspeiser: boolean
): VdePruefResult {
  const anf = getVdeAnforderung(se, p_kw, isEinspeiser);
  const cos_phi_ok = cos_phi >= anf.cos_phi_min;

  const hinweise: string[] = [...anf.bemerkungen];
  const warnungen: string[] = [];

  if (!cos_phi_ok) {
    warnungen.push(
      `cos(phi) = ${cos_phi} liegt unter Mindestanforderung ${anf.cos_phi_min} nach ${anf.regelwerk}`
    );
  }

  if (anf.zertifikat_erforderlich) {
    hinweise.push('Zertifizierung vor Inbetriebnahme einplanen (Vorlaufzeit 4-12 Wochen)');
  }

  if (anf.netzvertraeglichkeit_studie) {
    hinweise.push('Netzvertraeglichkeitspruefung beim NB beauftragen (Kosten ca. 5.000-25.000 EUR)');
  }

  if (anf.anlagenzertifikat) {
    hinweise.push('Anlagenzertifikat bei akkreditierter Stelle beauftragen');
  }

  return { regelwerk: anf.regelwerk, anforderung: anf, cos_phi_ok, cos_phi_eingabe: cos_phi, hinweise, warnungen };
}
