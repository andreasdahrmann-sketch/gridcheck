// src/types/index.ts
// Zentrale Typdefinitionen GridCheck

export type Anlagentyp = "solar" | "wind" | "batterie" | "waermepumpe" | "ladepark" | "sonstiges";
export type Richtung = "einspeisung" | "bezug" | "bidirektional";
export type Spannungsebene = "NS" | "MS" | "HS";
export type Topologie =
  | "radial"
  | "ring"
  | "stich"
  | "stich_mit_notverbindung"
  | "ring_offen"
  | "ring_geschlossen"
  | "doppelstich"
  | "vermascht"
  | "unbekannt";
export type Leitungsart = "kabel" | "freileitung";
export type ConfidenceLevel = "A" | "B" | "C" | "D";
export type MachbarkeitStufe = "gruen" | "gelb" | "orange" | "rot";
export type Kostenklasse = "gering" | "mittel" | "hoch" | "sehr_hoch";
export type Projektreife = "idee" | "planung" | "genehmigt" | "baubereit";
export type N1DataSource = "unknown" | "planner_assumption" | "user_estimate" | "dso_verified";
export type ProjectComponentType =
  | "pv"
  | "wind"
  | "battery"
  | "load"
  | "charging"
  | "heat_pump"
  | "electrolyzer"
  | "substation"
  | "other";
export type StorageOperationMode =
  | "market"
  | "hybrid"
  | "partial_grid_support"
  | "grid_support"
  | "unknown";
export type ExportLimitMode = "none" | "fixed" | "dynamic" | "schedule";
export type RiskLevel = "niedrig" | "mittel" | "hoch";
export type RiskLevelWithUnknown = RiskLevel | "unbekannt";
export type StakeholderPriority = "kosten" | "zeit" | "netz" | "genehmigung" | "balanced";

export interface ProjectComponentInput {
  component_type: ProjectComponentType;
  label?: string;
  capacity_kw: number;
  energy_kwh?: number;
  max_export_kw?: number;
  max_import_kw?: number;
  controllable?: boolean;
}

export interface NetzanschlusspunktInput {
  max_export_kw?: number;
  max_import_kw?: number;
  export_limit_mode?: ExportLimitMode;
  own_transformer?: boolean;
  own_substation?: boolean;
  own_switchgear?: boolean;
  remote_metering_ready?: boolean;
  preferred_connection_note?: string;
}

export interface StorageProfileInput {
  has_storage?: boolean;
  operation_mode?: StorageOperationMode;
  power_kw?: number;
  energy_kwh?: number;
  grid_support_services?: string[];
  reactive_power_capable?: boolean;
  remote_control_capable?: boolean;
  schedule_based_dispatch?: boolean;
  dynamic_export_limit?: boolean;
  peak_shaving?: boolean;
  curtailment_ready?: boolean;
  notes?: string;
}

export interface EnvironmentalRouteInput {
  route_length_km?: number;
  crossings_count?: number;
  protected_area_touch?: boolean;
  water_protection_area?: boolean;
  forest_crossing?: boolean;
  third_party_land?: boolean;
  noise_sensitive_area?: boolean;
  route_complexity?: RiskLevelWithUnknown;
  mitigation_measures?: string[];
  notes?: string;
}

export interface StakeholderContextInput {
  customer_type?: "projektierer" | "speicherbetreiber" | "netzbetreiber" | "investor";
  priority_focus?: StakeholderPriority;
  investor_relevant?: boolean;
  netzbetreiber_dialog_needed?: boolean;
}

export interface N1TransformerInput {
  label?: string;
  sn_mva: number;
  belastung_aktuell_mw?: number;
}

export interface N1FeederInput {
  label?: string;
  i_max_a?: number;
  belastung_aktuell_a?: number;
  reserve_n1_a?: number;
  reserve_i_a?: number;
  primary?: boolean;
  verfuegbar_im_n1?: boolean;
  koppelbar?: boolean;
  datenquelle?: N1DataSource;
}

export interface UmspannwerkInput {
  datenquelle?: N1DataSource;
  trafos?: N1TransformerInput[];
  abgaenge?: N1FeederInput[];
}

export interface ProjectLocationInput {
  latitude?: number;
  longitude?: number;
  address_hint?: string;
  area_radius_m?: number;
}

export interface GridCheckInput {
  plz: string;
  ort?: string;
  anlagentyp: Anlagentyp;
  richtung: Richtung;
  anschlussleistung_kw: number;
  cos_phi: number;
  spannungsebene: Spannungsebene;
  topologie: Topologie;
  leitungsart?: Leitungsart;
  entfernung_km?: number;
  kabeltyp?: string;
  sk_min_mva?: number;
  sk_max_mva?: number;
  rx_verhaeltnis?: number;
  trafo_sr_kva?: number;
  trafo_uk_pct?: number;
  trafo_anzahl?: number;
  vorbelastung_pct?: number;
  netzkapazitaet_kw?: number;
  projektreife?: Projektreife;
  baugenehmigung_vorhanden?: boolean;
  foerderfrist?: string;
  antragsteller?: string;
  project_components?: ProjectComponentInput[];
  netzanschlusspunkt?: NetzanschlusspunktInput;
  storage_profile?: StorageProfileInput;
  environmental_route?: EnvironmentalRouteInput;
  stakeholder_context?: StakeholderContextInput;
  project_location?: ProjectLocationInput;
  restkapazitaet_ms_mva?: number;
  umschaltzeit_min?: number;
  n1_datengrundlage?: N1DataSource;
  umspannwerk?: UmspannwerkInput;
}

export interface Szenario {
  name: string;
  beschreibung: string;
  delta_u_pct: number;
  delta_u_isRise: boolean;
  trafo_auslastung_pct: number;
  leitung_auslastung_pct: number;
  ik_kA: number;
  bewertung: "ok" | "grenzwertig" | "kritisch";
}

export interface TeilScores {
  kapazitaet: number;
  spannung: number;
  kurzschluss: number;
  n1: number;
  datenqualitaet: number;
}

export interface ErweiterteScores {
  netzdienlichkeit: number;
  projektfit: number;
  umwelt_trasse: number;
  stakeholder_fit: number;
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

export interface ProjektprofilResult {
  total_installed_kw: number;
  component_count: number;
  is_hybrid: boolean;
  component_summary: string[];
  max_export_kw: number;
  max_import_kw: number;
  summary: string;
}

export interface SpeicherBewertungResult {
  relevant: boolean;
  operation_mode: StorageOperationMode;
  flexibility_score: number;
  grid_support_score: number;
  benefit_flags: string[];
  warnings: string[];
  summary: string;
  disclaimer: string;
}

export interface RouteEnvironmentResult {
  risk_score: number;
  risk_level: RiskLevel;
  drivers: string[];
  mitigation: string[];
  summary: string;
}

export interface StakeholderBewertungResult {
  netzbetreiber_score: number;
  projektierer_score: number;
  umsetzung_score: number;
  konflikt_level: RiskLevel;
  konflikt_summary: string;
  recommended_focus: string;
}

export interface TransparenzResult {
  assumptions: string[];
  disclaimers: string[];
  confidence_notes: string[];
}

export type N1Bewertung = "GRUEN" | "GELB" | "ROT" | "NICHT_GEPRUEFT";

export interface N1AnnahmeResult {
  feld?: string;
  wert?: unknown;
  quelle?: string;
  begruendung?: string;
}

export interface N1ComponentResult {
  bewertung: N1Bewertung;
  begruendung_technisch?: string;
  begruendung_klartext?: string;
  auslastung_n1_prozent?: number | null;
  engpass_trafo_idx?: number;
  iz_a?: number | null;
  i_n1_a?: number | null;
  primaer_abgang_label?: string | null;
  engpass_abgang_label?: string | null;
  abgaenge_gesamt?: number;
  abgaenge_auswertbar?: number;
  projektstrom_a?: number | null;
  beste_reserve_a?: number | null;
  reserve_ratio?: number | null;
  delta_u_n1_prozent?: number | null;
  grenze_prozent?: number | null;
}

export interface N1SummaryResult {
  bewertung: N1Bewertung;
  engpass_komponente?: string;
  n1_klasse?: string;
  konfidenz?: number;
  stufenbegruendung?: string;
  dso_daten_vorhanden?: boolean;
  empfehlungen: string[];
  nachweise_vorhanden: string[];
  nachweise_fehlend: string[];
}

export interface N1AnalysisResult {
  n1_topologie: N1ComponentResult;
  n1_leitung: N1ComponentResult;
  n1_abgang: N1ComponentResult;
  n1_trafo: N1ComponentResult;
  n1_spannung: N1ComponentResult;
  gesamt: N1SummaryResult;
  annahmen: N1AnnahmeResult[];
  berechnungs_version?: string;
  backend?: string;
}

export interface N1Result {
  n1_sicher: boolean | null;
  bewertung?: N1Bewertung;
  topologie?: string;
  topologie_text: string;
  leitung_n1?: boolean | null;
  leitung_text?: string;
  n1_auslastung_prozent?: number | null;
  trafo_n1?: boolean | null;
  detail_text?: string;
  n1_klasse?: string;
  n1_konfidenz?: number;
  engpass_komponente?: string;
  stufenbegruendung?: string;
  nachweise_vorhanden: string[];
  nachweise_fehlend: string[];
  dso_daten_vorhanden?: boolean;
  detail_empfehlungen: string[];
  detail_annahmen: string[];
}

export interface KiCalibrationResult {
  samples: number;
  trefferquote: number;
  durchschnittlicher_fehler: number;
  bias?: number;
  kalibrierungsfaktor: number;
  bestaetigungsquote?: number;
  status: string;
}

export interface KiFeedbackLoopResult {
  samples_total: number;
  linked_samples: number;
  bestaetigt: number;
  korrigiert: number;
  bestaetigungsquote: number;
  coverage_ratio: number;
  anomaly_feedbacks: number;
  status: string;
  last_feedback_at?: string | null;
}

export interface KiAnomalieResult {
  is_anomaly: boolean;
  severity: RiskLevel;
  score: number;
  flags: string[];
  summary: string;
}

export interface KiLearningResult {
  konfidenz: number;
  konfidenz_prozent: number;
  aehnliche_faelle: number;
  kalibrierung: KiCalibrationResult;
  feedback_loop: KiFeedbackLoopResult;
  anomalie_check: KiAnomalieResult;
  hinweise: string[];
}

export interface RevisionMeta {
  revisionsnummer?: number;
  uuid?: string;
  timestamp?: string;
  schema_version?: string;
  engine_version?: string;
  previous_hash?: string;
  hash?: string;
  dry_run?: boolean;
  fehler?: string;
}

export interface BillingAccessMeta {
  offer_id?: string;
  package_scope?: string;
  usage_bucket?: string;
  report_scope?: string;
  ops_followup_required?: boolean;
}

export interface AnalysisHistoryMeta {
  analysis_run_id?: number;
}

// VDE-Pruefung
export interface VdePruefResult {
  regelwerk: string;
  cos_phi_ok: boolean;
  cos_phi_eingabe: number;
  hinweise: string[];
  warnungen: string[];
  zertifikat_erforderlich: boolean;
  anlagenzertifikat: boolean;
  netzvertraeglichkeit_studie: boolean;
  schutzkonzept_erforderlich: boolean;
}

// Sk-Bandbreite
export interface SkBandbreiteResult {
  region: string;
  min_mva: number;
  typ_mva: number;
  max_mva: number;
  verwendeter_wert_mva: number;
}

export interface KostenBandbreiteResult {
  niedrig_eur: number;
  basis_eur: number;
  hoch_eur: number;
  confidence_pct?: number;
  source?: string;
  assumptions: string[];
  drivers: string[];
}

export interface TechnicalDetailsResult {
  spannungsfall: {
    delta_u_prozent?: number;
    richtung?: string;
    bewertung?: string;
    cos_phi?: number;
    cos_phi_quelle?: string;
    cos_phi_annahme?: string;
  };
  kurzschluss: {
    ik_max_ka?: number;
    ik_min_ka?: number;
    sk_mva?: number;
    ik_referenz_ka?: number;
    ik_band_min_ka?: number;
    ik_band_max_ka?: number;
    vorlaeufig?: boolean;
    hinweis?: string;
  };
  leitung: {
    typ?: string;
    querschnitt_mm2?: number;
    material?: string;
    i_max_a?: number;
  };
  trasse: {
    entfernung_km?: number;
    heuristisch?: boolean;
    annahme?: string;
  };
}

export interface PowerLimitHintResult {
  label: string;
  typical_max_kw: number;
  screening_upper_kw: number;
  hinweis: string;
  eingabe_kw?: number;
  ueber_typischem_richtwert?: boolean;
}

/** Engine block `grid_calculation_v2` — authoritative calculation in Python backend. */
export type { GridCalculationV2 } from "@/lib/schemas/grid-calculation";

export interface GridCheckResult {
  machbar: boolean;
  machbarkeit_stufe: MachbarkeitStufe;
  einschraenkungen: string[];
  warnings: string[];
  empfehlungen: string[];
  connection_type_label?: string;
  technical_details?: TechnicalDetailsResult;
  grid_calculation_v2?: import("@/lib/schemas/grid-calculation").GridCalculationV2;
  power_limit_hints?: PowerLimitHintResult;
  p_max_kW: number;
  q_max_kvar: number;
  s_max_kVA: number;
  i_betrieb_A: number;
  szenarien: Szenario[];
  worst_case: Szenario;
  delta_u_pct: number;
  delta_u_isRise: boolean;
  spannungsbewertung: string;
  kurzschluss: KurzschlussResult;
  trafo_auslastung_pct: number;
  leitung_auslastung_pct: number;
  n1_prescreen_ok: boolean | null;
  n1_prescreen_detail: string;
  n1_hinweis: string;
  n1: N1Result;
  n1_analyse: N1AnalysisResult;
  blindleistung: BlindleistungResult;
  netzrueckwirkung: NetzrueckwirkungResult;
  nvp_bezeichnung: string;
  nvp_entfernung_km: number;
  nvp_freie_kapazitaet_kw: number;
  kosten_indikation_eur: number;
  kostenklasse: Kostenklasse;
  geschaetzte_bearbeitungszeit_wochen: number;
  netzausbau_erforderlich: boolean;
  teil_scores: TeilScores;
  erweiterte_scores: ErweiterteScores;
  score: number;
  konfidenz: number;
  daten_confidence: ConfidenceLevel;
  z_quelle_ohm: number;
  z_trafo_ohm: number;
  z_leitung_ohm: number;
  z_gesamt_ohm: number;
  projektprofil: ProjektprofilResult;
  speicher_bewertung: SpeicherBewertungResult;
  route_environment: RouteEnvironmentResult;
  stakeholder_bewertung: StakeholderBewertungResult;
  transparenz: TransparenzResult;
  ki: KiLearningResult;
  revision?: RevisionMeta;
  billing_access?: BillingAccessMeta;
  history?: AnalysisHistoryMeta;
  // NEU: VDE + Sk-Bandbreite
  vde_pruefung: VdePruefResult;
  sk_bandbreite: SkBandbreiteResult;
  kosten_bandbreite?: KostenBandbreiteResult;
}
