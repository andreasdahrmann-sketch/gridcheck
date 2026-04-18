// src/types/index.ts
// Zentrale Typdefinitionen GridCheck

export type Anlagentyp = 'solar' | 'wind' | 'batterie' | 'waermepumpe' | 'ladepark' | 'sonstiges';
export type Richtung = 'einspeisung' | 'bezug' | 'bidirektional';
export type Spannungsebene = 'NS' | 'MS' | 'HS';
export type Topologie = 'radial' | 'ring' | 'vermascht' | 'unbekannt';
export type ConfidenceLevel = 'A' | 'B' | 'C' | 'D';
export type MachbarkeitStufe = 'gruen' | 'gelb' | 'orange' | 'rot';
export type Kostenklasse = 'gering' | 'mittel' | 'hoch' | 'sehr_hoch';

export interface GridCheckInput {
  plz: string;
  ort?: string;
  anlagentyp: Anlagentyp;
  richtung: Richtung;
  anschlussleistung_kw: number;
  cos_phi: number;
  spannungsebene: Spannungsebene;
  topologie: Topologie;
  entfernung_km?: number;
  kabeltyp?: string;
  // Optionale Netzdaten (wenn bekannt -> hoehere Confidence)
  sk_min_mva?: number;
  sk_max_mva?: number;
  rx_verhaeltnis?: number;
  trafo_sr_kva?: number;
  trafo_uk_pct?: number;
  trafo_anzahl?: number;
  vorbelastung_pct?: number;
  netzkapazitaet_kw?: number;
}

export interface Szenario {
  name: string;
  beschreibung: string;
  delta_u_pct: number;
  delta_u_isRise: boolean;
  trafo_auslastung_pct: number;
  leitung_auslastung_pct: number;
  ik_kA: number;
  bewertung: 'ok' | 'grenzwertig' | 'kritisch';
}

export interface TeilScores {
  kapazitaet: number;
  spannung: number;
  kurzschluss: number;
  n1: number;
  datenqualitaet: number;
}

export interface KurzschlussResult {
  ik_min_kA: number;
  ik_max_kA: number;
  sk_am_nvp_mva: number;
  bewertung: string;
}

export interface BlindleistungResult {
  q_bedarf_kvar: number;
  q_reserve_kvar: number;
  kompensation_empfohlen: boolean;
  empfehlung: string;
}

export interface NetzrueckwirkungResult {
  leistungsverhaeltnis: number;
  flickerrisiko: boolean;
  oberschwingungsrisiko: boolean;
  bewertung: string;
}

export interface Confidence {
  level: ConfidenceLevel;
  score: number;
  fehlende_daten: string[];
}

export interface GridCheckResult {
  machbar: boolean;
  machbarkeit_stufe: MachbarkeitStufe;
  einschraenkungen: string[];
  empfehlungen: string[];
  // Elektrische Werte
  p_max_kW: number;
  q_max_kvar: number;
  s_max_kVA: number;
  i_betrieb_A: number;
  // Szenarien
  szenarien: Szenario[];
  worst_case: Szenario;
  // Spannung
  delta_u_pct: number;
  delta_u_isRise: boolean;
  spannungsbewertung: string;
  // Kurzschluss
  kurzschluss: KurzschlussResult;
  // Auslastung
  trafo_auslastung_pct: number;
  leitung_auslastung_pct: number;
  // N-1
  n1_prescreen_ok: boolean;
  n1_prescreen_detail: string;
  n1_hinweis: string;
  // Blindleistung
  blindleistung: BlindleistungResult;
  // Netzrueckwirkung
  netzrueckwirkung: NetzrueckwirkungResult;
  // NVP
  nvp_bezeichnung: string;
  nvp_entfernung_km: number;
  nvp_freie_kapazitaet_kw: number;
  // Kosten
  kosten_indikation_eur: number;
  kostenklasse: Kostenklasse;
  geschaetzte_bearbeitungszeit_wochen: number;
  netzausbau_erforderlich: boolean;
  // Bewertung
  teil_scores: TeilScores;
  score: number;
  konfidenz: number;
  daten_confidence: ConfidenceLevel;
  // Impedanzen
  z_quelle_ohm: number;
  z_trafo_ohm: number;
  z_leitung_ohm: number;
  z_gesamt_ohm: number;
}
