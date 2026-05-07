import type {
  GridCheckInput,
  GridCheckResult,
  MachbarkeitStufe,
  Szenario,
  Spannungsebene,
} from "@/types";

type ApiErrorDetail = {
  code?: string;
  message?: string;
  hint?: string | null;
};

export class AnalyzeApiError extends Error {
  readonly status: number;
  readonly detail: ApiErrorDetail | null;

  constructor(status: number, message: string, detail: ApiErrorDetail | null = null) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

const BASE = "/api/backend/api/v1";

function mapSpannungsebeneToKv(se: Spannungsebene): number {
  if (se === "NS") return 0.4;
  if (se === "MS") return 20;
  return 110;
}

function mapRichtung(r: GridCheckInput["richtung"]): "Einspeisung" | "Entnahme" | "Speicher" {
  if (r === "bezug") return "Entnahme";
  if (r === "bidirektional") return "Speicher";
  return "Einspeisung";
}

function mapAnlagentyp(t: GridCheckInput["anlagentyp"]): string {
  if (t === "solar") return "PV";
  if (t === "batterie") return "BESS";
  return t.toUpperCase();
}

function mapKostenklasse(investition: number): GridCheckResult["kostenklasse"] {
  if (investition < 10000) return "gering";
  if (investition < 50000) return "mittel";
  if (investition < 200000) return "hoch";
  return "sehr_hoch";
}

function mapFazitToStufe(entscheidung?: string): MachbarkeitStufe {
  if (entscheidung === "A") return "gruen";
  if (entscheidung === "B") return "gelb";
  return "rot";
}

function toUiSzenarien(raw: unknown): Szenario[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item: any) => {
    const du = Number(item?.spannung?.delta_u_prozent ?? 0);
    const trafo = Number(item?.trafo?.auslastung_prozent ?? 0);
    const leitung = Number(item?.thermisch?.auslastung_prozent ?? 0);
    const status = String(item?.thermisch?.bewertung ?? "GELB");
    const bewertung =
      status === "GRUEN" ? "ok" : status === "GELB" ? "grenzwertig" : "kritisch";
    return {
      name: String(item?.name ?? "Szenario"),
      beschreibung: String(item?.beschreibung ?? ""),
      delta_u_pct: Number(du.toFixed(3)),
      delta_u_isRise: String(item?.spannung?.richtung ?? "").toLowerCase().includes("anhebung"),
      trafo_auslastung_pct: Number(trafo.toFixed(1)),
      leitung_auslastung_pct: Number(leitung.toFixed(1)),
      ik_kA: Number(item?.kurzschluss?.ik_max_ka ?? 0),
      bewertung,
    };
  });
}

function pickWorstCase(szenarien: Szenario[]): Szenario {
  if (szenarien.length === 0) {
    return {
      name: "Worst Case",
      beschreibung: "",
      delta_u_pct: 0,
      delta_u_isRise: false,
      trafo_auslastung_pct: 0,
      leitung_auslastung_pct: 0,
      ik_kA: 0,
      bewertung: "grenzwertig",
    };
  }
  return szenarien.reduce((w, s) => (Math.abs(s.delta_u_pct) > Math.abs(w.delta_u_pct) ? s : w));
}

function mapResponseToUi(res: any, input: GridCheckInput): GridCheckResult {
  const szenarien = toUiSzenarien(res?.szenarien);
  const worst = pickWorstCase(szenarien);
  const score = Number(res?.scores?.gesamt ?? 0);
  const investition = Number(res?.kosten?.investition_gesamt_eur ?? 0);
  const dq = String(res?.datenqualitaet?.klasse ?? "D") as GridCheckResult["daten_confidence"];

  return {
    machbar: String(res?.fazit?.entscheidung ?? "C") !== "C",
    machbarkeit_stufe: mapFazitToStufe(res?.fazit?.entscheidung),
    einschraenkungen: Array.isArray(res?.warnungen) ? res.warnungen : [],
    empfehlungen: Array.isArray(res?.empfehlungen) ? res.empfehlungen : [],
    p_max_kW: Number((res?.pqs?.p_mw ?? input.anschlussleistung_kw / 1000) * 1000),
    q_max_kvar: Number((res?.pqs?.q_mvar ?? 0) * 1000),
    s_max_kVA: Number((res?.pqs?.s_mva ?? 0) * 1000),
    i_betrieb_A: Number(res?.thermisch?.i_betrieb_gesamt_a ?? 0),
    szenarien,
    worst_case: worst,
    delta_u_pct: Number(res?.spannung?.delta_u_prozent ?? worst.delta_u_pct),
    delta_u_isRise: String(res?.spannung?.richtung ?? "").toLowerCase().includes("anhebung"),
    spannungsbewertung: String(res?.spannung?.text ?? ""),
    kurzschluss: {
      ik_min_kA: Number(res?.kurzschluss?.ik_min_ka ?? 0),
      ik_max_kA: Number(res?.kurzschluss?.ik_max_ka ?? 0),
      sk_am_nvp_mva: Number(res?.kurzschluss?.sk_mva ?? 0),
      bewertung: String(res?.kurzschluss?.text ?? ""),
    },
    trafo_auslastung_pct: Number(res?.trafo?.auslastung_prozent ?? 0),
    leitung_auslastung_pct: Number(res?.thermisch?.auslastung_prozent ?? 0),
    n1_prescreen_ok: Boolean(res?.n1?.n1_sicher),
    n1_prescreen_detail: String(res?.n1?.topologie_text ?? ""),
    n1_hinweis: String(res?.n1?.leitung_text ?? ""),
    blindleistung: {
      q_bedarf_kvar: Number((res?.pqs?.q_mvar ?? 0) * 1000),
      q_reserve_kvar: 0,
      kompensation_empfohlen: true,
      empfehlung: "Blindleistungsvorgaben gemaess VNB im Detail pruefen.",
    },
    netzrueckwirkung: {
      leistungsverhaeltnis: Number(res?.kurzschluss?.rueckwirkung_ratio ?? 0),
      flickerrisiko: Number(res?.kurzschluss?.rueckwirkung_ratio ?? 0) > 0.02,
      oberschwingungsrisiko: Number(res?.kurzschluss?.rueckwirkung_ratio ?? 0) > 0.05,
      bewertung: String(res?.kurzschluss?.rw_text ?? ""),
    },
    nvp_bezeichnung: `NVP-${input.plz}`,
    nvp_entfernung_km: Number(input.entfernung_km ?? 0),
    nvp_freie_kapazitaet_kw: Number(input.netzkapazitaet_kw ?? 0),
    kosten_indikation_eur: investition,
    kostenklasse: mapKostenklasse(investition),
    geschaetzte_bearbeitungszeit_wochen: 8,
    netzausbau_erforderlich:
      String(res?.fazit?.entscheidung ?? "C") === "C" ||
      Number(res?.thermisch?.auslastung_prozent ?? 0) > 100,
    teil_scores: {
      kapazitaet: Number(res?.scores?.kapazitaet ?? 0),
      spannung: Number(res?.scores?.spannung ?? 0),
      kurzschluss: Number(res?.scores?.kurzschluss ?? 0),
      n1: Number(res?.scores?.versorgungssicherheit ?? 0),
      datenqualitaet: Number(res?.scores?.datenqualitaet ?? 0),
    },
    score,
    konfidenz: Number(res?.ki?.konfidenz_prozent ?? 0),
    daten_confidence: dq,
    z_quelle_ohm: Number(res?.impedanz?.r_q ?? 0),
    z_trafo_ohm: Number(res?.impedanz?.r_t ?? 0),
    z_leitung_ohm: Number(res?.impedanz?.r_l ?? 0),
    z_gesamt_ohm: Number(res?.impedanz?.z_ges ?? 0),
    vde_pruefung: {
      regelwerk: "VDE-AR-N 4105/4110/4120",
      cos_phi_ok: Number(input.cos_phi) >= 0.9,
      cos_phi_eingabe: Number(input.cos_phi),
      hinweise: [],
      warnungen: [],
      zertifikat_erforderlich: false,
      anlagenzertifikat: false,
      netzvertraeglichkeit_studie: false,
      schutzkonzept_erforderlich: false,
    },
    sk_bandbreite: {
      region: "Unbekannt",
      min_mva: Number(res?.kurzschluss?.sk_mva ?? 0),
      typ_mva: Number(res?.kurzschluss?.sk_mva ?? 0),
      max_mva: Number(res?.kurzschluss?.sk_mva ?? 0),
      verwendeter_wert_mva: Number(res?.kurzschluss?.sk_mva ?? 0),
    },
  };
}

export async function analyzeGridcheck(input: GridCheckInput): Promise<GridCheckResult> {
  const payload = {
    nennspannung: mapSpannungsebeneToKv(input.spannungsebene),
    leistung_mw: Number(input.anschlussleistung_kw) / 1000,
    leitungstyp: input.kabeltyp ?? "NA2XS2Y240",
    entfernung_km: Number(input.entfernung_km ?? 5),
    anschlussart: mapRichtung(input.richtung),
    anlagentyp: mapAnlagentyp(input.anlagentyp),
    plz: input.plz,
    cos_phi: Number(input.cos_phi),
    parallele_systeme: 1,
    redundanz: input.topologie !== "radial",
    p_kw: Number(input.anschlussleistung_kw),
    bestehende_einspeisung_mw: 0,
    sk_mva: input.sk_min_mva,
    trafo_s_mva: input.trafo_sr_kva ? input.trafo_sr_kva / 1000 : undefined,
    uk_prozent: input.trafo_uk_pct,
    bestand_auslastung_prozent: input.vorbelastung_pct,
    temperatur_c: 20,
  };

  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });

  let body: any = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  if (!res.ok) {
    const detail = body?.detail && typeof body.detail === "object" ? body.detail : null;
    const msg =
      detail?.message ??
      (typeof body?.detail === "string" ? body.detail : `Analyse fehlgeschlagen (HTTP ${res.status})`);
    throw new AnalyzeApiError(res.status, msg, detail);
  }

  return mapResponseToUi(body, input);
}
