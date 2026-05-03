// src/lib/engine.ts
// GridCheck Rechenkern v2 - P/Q/S getrennt, Szenarien, Impedanzmodell, VDE-Pruefung, Sk-Bandbreite
import {
  kW_to_W, W_to_kW, kV_to_V, MVA_to_VA, VA_to_kVA, VA_to_MVA, kVA_to_VA,
  A_to_kA, calcS_from_P_cosPhi, calcQ_from_P_cosPhi,
  calcI_from_S, calcZq, calcZtrafo, calcRX_from_Z, calcDeltaU_pct, calcIk
} from './units';
import type {
  GridCheckInput, GridCheckResult, Szenario, TeilScores,
  KurzschlussResult, BlindleistungResult, NetzrueckwirkungResult,
  VdePruefResult, SkBandbreiteResult,
  Confidence, ConfidenceLevel, MachbarkeitStufe, Kostenklasse, Topologie, Spannungsebene
} from '@/types';

// ============================================================
// Referenzdaten je Spannungsebene
// ============================================================
interface VorgabeLevel {
  key: string;
  u_nenn_kV: number;
  sk_typ_mva: number;
  rx_typ: number;
  trafo_sr_kva: number;
  trafo_uk_pct: number;
  trafo_anzahl: number;
  delta_u_max_pct: number;
  i_therm_A: number;
  r_leitung_ohm_per_km: number;
  x_leitung_ohm_per_km: number;
}

function getVorgabe(se: Spannungsebene): VorgabeLevel {
  switch (se) {
    case 'NS': return {
      key:'NS', u_nenn_kV:0.4, sk_typ_mva:10, rx_typ:0.5, trafo_sr_kva:630,
      trafo_uk_pct:4, trafo_anzahl:1, delta_u_max_pct:3, i_therm_A:400,
      r_leitung_ohm_per_km:0.32, x_leitung_ohm_per_km:0.08,
    };
    case 'MS': return {
      key:'MS', u_nenn_kV:20, sk_typ_mva:250, rx_typ:0.3, trafo_sr_kva:20000,
      trafo_uk_pct:12, trafo_anzahl:2, delta_u_max_pct:2, i_therm_A:600,
      r_leitung_ohm_per_km:0.12, x_leitung_ohm_per_km:0.11,
    };
    default: return {
      key:'HS', u_nenn_kV:110, sk_typ_mva:2000, rx_typ:0.1, trafo_sr_kva:40000,
      trafo_uk_pct:14, trafo_anzahl:2, delta_u_max_pct:1, i_therm_A:1000,
      r_leitung_ohm_per_km:0.06, x_leitung_ohm_per_km:0.3,
    };
  }
}

// ============================================================
// PLZ-Heuristik fuer Entfernung und Kapazitaet
// ============================================================
function schaetzeEntfernung(plz: string, se: Spannungsebene): number {
  const p = parseInt(plz.substring(0, 2)) || 50;
  const base = 3; // MS-Netz
  const factor = p < 20 ? 1.3 : p < 50 ? 1.0 : p < 80 ? 1.1 : 1.4;
  return Math.round(base * factor * 10) / 10;
}

function schaetzeNVPKapazitaet(plz: string, vl: VorgabeLevel): number {
  const p = parseInt(plz.substring(0, 2)) || 50;
  const trafoKap = W_to_kW(kVA_to_VA(vl.trafo_sr_kva) * vl.trafo_anzahl);
  const factor = p < 30 ? 0.4 : p < 60 ? 0.35 : 0.3;
  return Math.round(trafoKap * factor);
}

// ============================================================
// Confidence (Datenqualitaet)
// ============================================================
function berechneConfidence(input: GridCheckInput): Confidence {
  const fehlend: string[] = [];
  let score = 100;
  if (!input.sk_min_mva) { fehlend.push('Sk_min'); score -= 15; }
  if (!input.sk_max_mva) { fehlend.push('Sk_max'); score -= 10; }
  if (!input.rx_verhaeltnis) { fehlend.push('R/X-Verhaeltnis'); score -= 10; }
  if (!input.trafo_sr_kva) { fehlend.push('Trafo-Bemessungsleistung'); score -= 10; }
  if (!input.trafo_uk_pct) { fehlend.push('Trafo uk%'); score -= 10; }
  if (!input.entfernung_km) { fehlend.push('Leitungsentfernung'); score -= 10; }
  if (!input.netzkapazitaet_kw) { fehlend.push('Freie Netzkapazitaet'); score -= 10; }
  if (!input.vorbelastung_pct && input.vorbelastung_pct !== 0) { fehlend.push('Vorbelastung'); score -= 5; }
  score = Math.max(score, 0);
  let level: ConfidenceLevel = 'A';
  if (score < 40) level = 'D';
  else if (score < 60) level = 'C';
  else if (score < 80) level = 'B';
  return { level, score, fehlende_daten: fehlend };
}

// ============================================================
// Impedanzmodell
// ============================================================
interface Impedanzen {
  zq_ohm: number;
  zt_ohm: number;
  rl_ohm: number;
  xl_ohm: number;
  r_ohm: number;
  x_ohm: number;
  z_ohm: number;
}

function berechneImpedanzen(vl: VorgabeLevel, sk_mva: number, rx: number, trafoSr_kva: number, trafoUk_pct: number, entf_km: number): Impedanzen {
  const u_V = kV_to_V(vl.u_nenn_kV);
  const zq = calcZq(u_V, MVA_to_VA(sk_mva));
  const zt = calcZtrafo(u_V, kVA_to_VA(trafoSr_kva), trafoUk_pct);
  const rl = vl.r_leitung_ohm_per_km * entf_km;
  const xl = vl.x_leitung_ohm_per_km * entf_km;
  const { r: rq, x: xq } = calcRX_from_Z(zq, rx);
  const { r: rt, x: xt } = calcRX_from_Z(zt, rx);
  const r_total = rq + rt + rl;
  const x_total = xq + xt + xl;
  const z_total = Math.sqrt(r_total ** 2 + x_total ** 2);
  return { zq_ohm: zq, zt_ohm: zt, rl_ohm: rl, xl_ohm: xl, r_ohm: r_total, x_ohm: x_total, z_ohm: z_total };
}

// ============================================================
// Szenarien
// ============================================================
function berechneSzenarien(p_W: number, q_var: number, s_VA: number, vl: VorgabeLevel, imp: Impedanzen, input: GridCheckInput, isEinspeiser: boolean): Szenario[] {
  const u_V = kV_to_V(vl.u_nenn_kV);
  const i_A = calcI_from_S(s_VA, u_V);
  const vorbelastung = (input.vorbelastung_pct ?? 60) / 100;

  function makeSzenario(name: string, beschr: string, vorb: number, nTrafos: number): Szenario {
    const trafoS = kVA_to_VA(vl.trafo_sr_kva) * nTrafos;
    const trafoAusl = ((vorb * trafoS) + s_VA) / trafoS * 100;
    const leitAusl = i_A / vl.i_therm_A * 100;
    const du = calcDeltaU_pct(p_W, q_var, imp.r_ohm, imp.x_ohm, u_V, isEinspeiser);
    const ik = A_to_kA(calcIk(u_V, imp.z_ohm));
    let bew: 'ok' | 'grenzwertig' | 'kritisch' = 'ok';
    if (Math.abs(du.delta_u_pct) > vl.delta_u_max_pct || trafoAusl > 100) bew = 'kritisch';
    else if (Math.abs(du.delta_u_pct) > vl.delta_u_max_pct * 0.8 || trafoAusl > 80) bew = 'grenzwertig';
    return {
      name, beschreibung: beschr,
      delta_u_pct: du.delta_u_pct, delta_u_isRise: du.isRise,
      trafo_auslastung_pct: Math.round(trafoAusl * 10) / 10,
      leitung_auslastung_pct: Math.round(leitAusl * 10) / 10,
      ik_kA: Math.round(ik * 100) / 100,
      bewertung: bew
    };
  }

  const nTrafo = input.trafo_anzahl ?? vl.trafo_anzahl;
  return [
    makeSzenario('Normalbetrieb', 'Typische Vorbelastung, alle Betriebsmittel verfuegbar', vorbelastung, nTrafo),
    makeSzenario('Schwachlast', 'Geringe Vorbelastung (20%), maximale Spannungsanhebung', 0.2, nTrafo),
    makeSzenario('Starklast', 'Hohe Vorbelastung (85%), kritisch fuer Auslastung', 0.85, nTrafo),
    makeSzenario('N-1 (1 Trafo weniger)', 'Ein Trafo faellt aus, Restkapazitaet', vorbelastung, Math.max(nTrafo - 1, 1)),
  ];
}

// ============================================================
// Kurzschluss
// ============================================================
function berechneKurzschluss(imp: Impedanzen, u_V: number, sk_min_mva: number, sk_max_mva: number): KurzschlussResult {
  const ik_min = A_to_kA(calcIk(u_V, imp.z_ohm * (sk_max_mva / Math.max(sk_min_mva, 1))));
  const ik_max = A_to_kA(calcIk(u_V, imp.z_ohm));
  const sk = VA_to_MVA(u_V * u_V / imp.z_ohm);
  let bew = 'Ausreichend';
  if (ik_min < 1 && u_V < 1000) bew = 'Ik_min zu gering fuer Schutzauslegung';
  else if (ik_max > 25) bew = 'Ik_max hoch - Schaltanlagenpruefung erforderlich';
  return { ik_min_kA: Math.round(ik_min * 100) / 100, ik_max_kA: Math.round(ik_max * 100) / 100, sk_am_nvp_mva: Math.round(sk * 10) / 10, bewertung: bew };
}

// ============================================================
// Blindleistung
// ============================================================
function berechneBlindleistung(q_var: number, s_VA: number, cos_phi: number): BlindleistungResult {
  const q_kvar = Math.round(q_var / 1000);
  const reserve = Math.round((s_VA * 0.1) / 1000);
  const kompEmpf = cos_phi < 0.95;
  let empf = 'Blindleistungsbedarf im Rahmen.';
  if (kompEmpf) empf = `Q-Kompensation empfohlen (cos_phi=${cos_phi}). Ziel: >= 0.95.`;
  return { q_bedarf_kvar: q_kvar, q_reserve_kvar: reserve, kompensation_empfohlen: kompEmpf, empfehlung: empf };
}

// ============================================================
// Netzrueckwirkung
// ============================================================
function berechneNetzrueckwirkung(s_VA: number, sk_VA: number): NetzrueckwirkungResult {
  const verh = s_VA / Math.max(sk_VA, 1);
  const flicker = verh > 0.02;
  const oberschw = verh > 0.05;
  let bew = 'Unkritisch';
  if (oberschw) bew = 'Netzrueckwirkungsgutachten erforderlich (Oberschwingungen)';
  else if (flicker) bew = 'Flickernachweis empfohlen';
  return { leistungsverhaeltnis: Math.round(verh * 1000) / 1000, flickerrisiko: flicker, oberschwingungsrisiko: oberschw, bewertung: bew };
}

// ============================================================
// N-1 Pre-Screen
// ============================================================
function berechneN1(szenarien: Szenario[], topo: Topologie) {
  const n1sz = szenarien.find(s => s.name.startsWith('N-1'));
  const ok = n1sz ? n1sz.bewertung !== 'kritisch' : false;
  const detail = n1sz ? `Trafo: ${n1sz.trafo_auslastung_pct}%, du: ${n1sz.delta_u_pct}%` : 'Kein N-1 Szenario';
  let hinweis = '';
  if (topo === 'radial') hinweis = 'Radiales Netz: keine Umschaltreserve. N-1 kritisch.';
  else if (topo === 'ring') hinweis = 'Ringnetz: Umschaltreserve vorhanden, N-1 moeglich.';
  else if (topo === 'vermascht') hinweis = 'Vermaschtes Netz: gute Redundanz.';
  else hinweis = 'Topologie unbekannt: konservative Bewertung.';
  return { ok, detail, hinweis };
}

// ============================================================
// VDE-Pruefung (NEU)
// ============================================================
  function berechneVdePruefung(input: GridCheckInput, vl: VorgabeLevel, p_kW: number, s_kVA: number): VdePruefResult {
    const hinweise: string[] = [];
    const warnungen: string[] = [];
    const regelwerk = 'VDE-AR-N 4110:2018-11';
    let zertifikat = false;
    const anlagenzert = true;
    const schutzkonzept = true;
    let nvStudie = false;

    // MS ist einzige Spannungsebene
    hinweise.push('MS-Anschluss: Anlagenzertifikat Typ B und Schutzkonzept erforderlich.');

    if (p_kW > 20000) {
      warnungen.push('Leistung > 20 MW: Ueberschreitet MS-Grenze, Ruecksprache mit Netzbetreiber erforderlich.');
    }

    // cos_phi Pruefung nach VDE-AR-N 4110 (MS: 0.95 <= cos_phi <= 1.0)
    let cosPhiOk = true;
    if (input.richtung === 'einspeisung' || input.richtung === 'bidirektional') {
      if (input.cos_phi < 0.95 || input.cos_phi > 1.0) {
        cosPhiOk = false;
        warnungen.push(`cos_phi=${input.cos_phi} ausserhalb VDE-Vorgabe 0.95-1.00 (MS, VDE-AR-N 4110).`);
      }
    }

    // Netzvertraeglichkeitsstudie
    if (p_kW > 1000) {
      nvStudie = true;
      hinweise.push('Leistung > 1 MW: Netzvertraeglichkeitsstudie empfohlen.');
    }

    // Einheitenzertifikat
    if (p_kW > 950 && (input.anlagentyp === 'solar' || input.anlagentyp === 'wind')) {
      zertifikat = true;
      hinweise.push('EZA >= 950 kW: Einheitenzertifikat erforderlich.');
    }

    return {
      regelwerk,
      cos_phi_ok: cosPhiOk,
      cos_phi_eingabe: input.cos_phi,
      hinweise,
      warnungen,
      zertifikat_erforderlich: zertifikat,
      anlagenzertifikat: anlagenzert,
      netzvertraeglichkeit_studie: nvStudie,
      schutzkonzept_erforderlich: schutzkonzept,
    };
  }

// ============================================================
// Sk-Bandbreite (NEU)
// ============================================================
function berechneSkBandbreite(input: GridCheckInput, vl: VorgabeLevel): SkBandbreiteResult {
  const p = parseInt(input.plz.substring(0, 2)) || 50;
  // Regionale Sk-Schaetzung basierend auf PLZ-Bereich
  let region = 'Mittel';
  let faktor = 1.0;
  if (p < 20) { region = 'Nord (laendlich)'; faktor = 0.75; }
  else if (p < 40) { region = 'Nordwest'; faktor = 0.9; }
  else if (p < 60) { region = 'Mitte/West'; faktor = 1.0; }
  else if (p < 80) { region = 'Sued'; faktor = 1.05; }
  else { region = 'Suedost (laendlich)'; faktor = 0.8; }

  const typ = vl.sk_typ_mva * faktor;
  const min = input.sk_min_mva ?? typ * 0.6;
  const max = input.sk_max_mva ?? typ * 1.3;
  const verwendet = input.sk_min_mva ?? min; // konservativ

  return {
    region,
    min_mva: Math.round(min * 10) / 10,
    typ_mva: Math.round(typ * 10) / 10,
    max_mva: Math.round(max * 10) / 10,
    verwendeter_wert_mva: Math.round(verwendet * 10) / 10,
  };
}

// ============================================================
// Teil-Scores und Gesamt-Score
// ============================================================
function berechneTeilScores(wc: Szenario, ks: KurzschlussResult, n1ok: boolean, conf: Confidence, vl: VorgabeLevel, nvpKap: number, p_kW: number): TeilScores {
  let kap = 25;
  if (p_kW > nvpKap) kap = 0;
  else if (p_kW > nvpKap * 0.8) kap = 10;
  else if (p_kW > nvpKap * 0.5) kap = 18;

  let sp = 25;
  const duAbs = Math.abs(wc.delta_u_pct);
  if (duAbs > vl.delta_u_max_pct) sp = 0;
  else if (duAbs > vl.delta_u_max_pct * 0.8) sp = 10;
  else if (duAbs > vl.delta_u_max_pct * 0.5) sp = 18;

  let ksScore = 20;
  if (ks.ik_min_kA < 0.5) ksScore = 5;
  else if (ks.ik_max_kA > 30) ksScore = 8;

  const n1Score = n1ok ? 15 : 3;
  const dq = Math.round(conf.score * 0.15);

  return { kapazitaet: kap, spannung: sp, kurzschluss: ksScore, n1: n1Score, datenqualitaet: dq };
}

function gesamtScore(ts: TeilScores): number {
  return ts.kapazitaet + ts.spannung + ts.kurzschluss + ts.n1 + ts.datenqualitaet;
}

// ============================================================
// Kosten / Bearbeitungszeit
// ============================================================
function schaetzeKosten(p_kW: number, vl: VorgabeLevel, ausbau: boolean, entf_km: number): number {
  let base = 5000; // MS-Netz
  base += p_kW * 25; // MS-Netz
  base += entf_km * 80000; // MS-Netz
  if (ausbau) base *= 1.8;
  return Math.round(base / 100) * 100;
}

function kostenklasse(k: number): Kostenklasse {
  if (k < 10000) return 'gering';
  if (k < 50000) return 'mittel';
  if (k < 200000) return 'hoch';
  return 'sehr_hoch';
}

function bearbeitungszeit(vl: VorgabeLevel, ausbau: boolean): number {
  const base = 8; // MS-Netz (Wochen)
  return ausbau ? base * 2 : base;
}

// ============================================================
// Empfehlungen
// ============================================================
function empfehlungen(wc: Szenario, ks: KurzschlussResult, bl: BlindleistungResult, nr: NetzrueckwirkungResult, n1ok: boolean, vl: VorgabeLevel, vde: VdePruefResult): string[] {
  const e: string[] = [];
  if (wc.trafo_auslastung_pct > 80) e.push('Trafoleistung erhoehen oder Lastmanagement einsetzen.');
  if (Math.abs(wc.delta_u_pct) > vl.delta_u_max_pct * 0.8) e.push('Spannungsregelung oder Q-Regelung pruefen.');
  if (bl.kompensation_empfohlen) e.push(bl.empfehlung);
  if (nr.flickerrisiko) e.push('Flickernachweis nach EN 61000-3-3/11 empfohlen.');
  if (nr.oberschwingungsrisiko) e.push('Netzrueckwirkungsgutachten erforderlich.');
  if (!n1ok) e.push('N-1-Sicherheit nicht gewaehrleistet. Redundanz pruefen.');
  if (wc.leitung_auslastung_pct > 70) e.push('Leitungsquerschnitt erhoehen oder kuerzere Trasse pruefen.');
  // VDE-Empfehlungen integrieren
  e.push(...vde.hinweise);
  if (vde.warnungen.length > 0) e.push(...vde.warnungen);
  if (e.length === 0) e.push('Anschluss technisch voraussichtlich machbar.');
  return e;
}

// ============================================================
// Spannungsbewertung
// ============================================================
function spannungsbewertung(du: number, max: number): string {
  const abs = Math.abs(du);
  if (abs <= max * 0.5) return 'Sehr gut';
  if (abs <= max * 0.8) return 'Akzeptabel';
  if (abs <= max) return 'Grenzwertig';
  return 'Ueberschreitung';
}

// ============================================================
// HAUPTFUNKTION
// ============================================================
export function berechneNetzanalyse(input: GridCheckInput): GridCheckResult {
  const vl = getVorgabe(input.spannungsebene);
  const u_V = kV_to_V(vl.u_nenn_kV);
  const isEinspeiser = input.richtung === 'einspeisung' || input.richtung === 'bidirektional';

  // P / Q / S intern in SI
  const p_kW = input.anschlussleistung_kw;
  const p_W = kW_to_W(p_kW);
  const s_VA = calcS_from_P_cosPhi(p_W, input.cos_phi);
  const q_var = calcQ_from_P_cosPhi(p_W, input.cos_phi);
  const i_A = calcI_from_S(s_VA, u_V);
  const s_kVA = VA_to_kVA(s_VA);

  // Netzdaten (mit Fallback auf Vorgaben)
  const sk_min = input.sk_min_mva ?? vl.sk_typ_mva * 0.8;
  const sk_max = input.sk_max_mva ?? vl.sk_typ_mva;
  const rx = input.rx_verhaeltnis ?? vl.rx_typ;
  const trafoSr = input.trafo_sr_kva ?? vl.trafo_sr_kva;
  const trafoUk = input.trafo_uk_pct ?? vl.trafo_uk_pct;
  const entf = input.entfernung_km ?? schaetzeEntfernung(input.plz, input.spannungsebene);
  const topo: Topologie = input.topologie ?? 'unbekannt';

  // Impedanzen
  const imp = berechneImpedanzen(vl, sk_min, rx, trafoSr, trafoUk, entf);

  // Szenarien
  const sz = berechneSzenarien(p_W, q_var, s_VA, vl, imp, input, isEinspeiser);
  const wc = sz.reduce((worst, s) => Math.abs(s.delta_u_pct) > Math.abs(worst.delta_u_pct) ? s : worst, sz[0]);

  // Kurzschluss
  const ksResult = berechneKurzschluss(imp, u_V, sk_min, sk_max);

  // Blindleistung
  const blResult = berechneBlindleistung(q_var, s_VA, input.cos_phi);

  // Netzrueckwirkung
  const nrResult = berechneNetzrueckwirkung(s_VA, MVA_to_VA(sk_min));

  // N-1
  const n1 = berechneN1(sz, topo);

  // VDE-Pruefung (NEU)
  const vdeResult = berechneVdePruefung(input, vl, p_kW, s_kVA);

  // Sk-Bandbreite (NEU)
  const skBand = berechneSkBandbreite(input, vl);

  // NVP Kapazitaet
  const nvpKap = input.netzkapazitaet_kw ?? schaetzeNVPKapazitaet(input.plz, vl);

  // Netzausbau
  const ausbau = p_kW > nvpKap || wc.trafo_auslastung_pct > 100 || Math.abs(wc.delta_u_pct) > vl.delta_u_max_pct;

  // Confidence
  const conf = berechneConfidence(input);

  // Teil-Scores
  const ts = berechneTeilScores(wc, ksResult, n1.ok, conf, vl, nvpKap, p_kW);
  const score = gesamtScore(ts);

  // Machbarkeit (VDE-Warnungen beeinflussen Score)
  let effScore = score;
  if (vdeResult.warnungen.length > 0) effScore = Math.max(effScore - 10, 0);

  let stufe: MachbarkeitStufe = 'gruen';
  if (effScore < 30) stufe = 'rot';
  else if (effScore < 50) stufe = 'orange';
  else if (effScore < 70) stufe = 'gelb';

  // Spannung
  const spBew = spannungsbewertung(wc.delta_u_pct, vl.delta_u_max_pct);

  // Kosten
  const kost = schaetzeKosten(p_kW, vl, ausbau, entf);

  // Einschraenkungen
  const einschr: string[] = [];
  if (conf.level === 'D') einschr.push('Ergebnis basiert auf PLZ-Heuristik (Datenqualitaet D). Reale Netzdaten erforderlich.');
  if (conf.level === 'C') einschr.push('Teilweise Referenzdaten (Datenqualitaet C). Validierung durch NB empfohlen.');
  if (topo === 'unbekannt') einschr.push('Topologie unbekannt: N-1-Bewertung nur konservativ.');
  if (vdeResult.warnungen.length > 0) einschr.push(...vdeResult.warnungen);

  return {
    machbar: effScore >= 30,
    machbarkeit_stufe: stufe,
    einschraenkungen: einschr,
    empfehlungen: empfehlungen(wc, ksResult, blResult, nrResult, n1.ok, vl, vdeResult),
    p_max_kW: Math.round(p_kW * 10) / 10,
    q_max_kvar: Math.round(q_var / 1000),
    s_max_kVA: Math.round(s_kVA * 10) / 10,
    i_betrieb_A: Math.round(i_A * 10) / 10,
    szenarien: sz,
    worst_case: wc,
    delta_u_pct: wc.delta_u_pct,
    delta_u_isRise: wc.delta_u_isRise,
    spannungsbewertung: spBew,
    kurzschluss: ksResult,
    trafo_auslastung_pct: wc.trafo_auslastung_pct,
    leitung_auslastung_pct: wc.leitung_auslastung_pct,
    n1_prescreen_ok: n1.ok,
    n1_prescreen_detail: n1.detail,
    n1_hinweis: n1.hinweis,
    blindleistung: blResult,
    netzrueckwirkung: nrResult,
    nvp_bezeichnung: `NVP-${input.plz}-${vl.key}`,
    nvp_entfernung_km: Math.round(entf * 10) / 10,
    nvp_freie_kapazitaet_kw: nvpKap,
    kosten_indikation_eur: kost,
    kostenklasse: kostenklasse(kost),
    geschaetzte_bearbeitungszeit_wochen: bearbeitungszeit(vl, ausbau),
    netzausbau_erforderlich: ausbau,
    teil_scores: ts,
    score: effScore,
    konfidenz: conf.score,
    daten_confidence: conf.level,
    z_quelle_ohm: Math.round(imp.zq_ohm * 1000) / 1000,
    z_trafo_ohm: Math.round(imp.zt_ohm * 1000) / 1000,
    z_leitung_ohm: Math.round(Math.sqrt(imp.rl_ohm ** 2 + imp.xl_ohm ** 2) * 1000) / 1000,
    z_gesamt_ohm: Math.round(imp.z_ohm * 1000) / 1000,
    vde_pruefung: vdeResult,
    sk_bandbreite: skBand,
  };
}

export const runGridCheck = berechneNetzanalyse;
