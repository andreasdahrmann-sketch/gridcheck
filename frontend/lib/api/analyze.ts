import type {
  ConfidenceLevel,
  GridCheckInput,
  GridCheckResult,
  MachbarkeitStufe,
  Szenario,
  Spannungsebene,
} from "@/types";
import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import type { BillingStatus } from "@/lib/api/billing";
import { bearerAuthHeaders } from "@/lib/api/session";

type ApiErrorDetail = {
  code?: string;
  message?: string;
  hint?: string | null;
  billing?: BillingStatus;
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
const REPORT_BASE = "/api/backend/api/v2/reports";

function hasValue(value: unknown) {
  return value !== undefined && value !== null && value !== "";
}

function readFiniteNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function validateAnalyzeInput(input: GridCheckInput) {
  const issues: string[] = [];
  const plz = input.plz?.trim() ?? "";

  if (!plz) {
    issues.push("Bitte eine PLZ eingeben.");
  } else if (!/^\d{5}$/.test(plz)) {
    issues.push("Bitte eine gueltige deutsche PLZ mit 5 Ziffern eingeben.");
  }

  const anschlussleistungKw = readFiniteNumber(input.anschlussleistung_kw);
  if (anschlussleistungKw === null || anschlussleistungKw <= 0 || anschlussleistungKw > 2_000_000) {
    issues.push("Die Anschlussleistung muss groesser als 0 und plausibel fuer den MVP sein.");
  }

  const cosPhi = readFiniteNumber(input.cos_phi);
  if (cosPhi === null || cosPhi < 0.8 || cosPhi > 1) {
    issues.push("cos phi muss zwischen 0,8 und 1,0 liegen.");
  }

  if (hasValue(input.entfernung_km)) {
    const entfernungKm = readFiniteNumber(input.entfernung_km);
    if (entfernungKm === null || entfernungKm <= 0 || entfernungKm > 500) {
      issues.push("Die Entfernung zum Anschlusskandidaten muss zwischen 0 und 500 km liegen.");
    }
  }

  if (hasValue(input.trafo_sr_kva)) {
    const trafoSrKva = readFiniteNumber(input.trafo_sr_kva);
    if (trafoSrKva === null || trafoSrKva <= 0) {
      issues.push("Die Trafogroesse muss groesser als 0 kVA sein.");
    }
  }

  if (hasValue(input.restkapazitaet_ms_mva)) {
    const restkapazitaet = readFiniteNumber(input.restkapazitaet_ms_mva);
    if (restkapazitaet === null || restkapazitaet <= 0) {
      issues.push("Die Restkapazitaet der MS muss groesser als 0 MVA sein.");
    }
  }

  const latitude = hasValue(input.project_location?.latitude) ? readFiniteNumber(input.project_location?.latitude) : null;
  const longitude = hasValue(input.project_location?.longitude) ? readFiniteNumber(input.project_location?.longitude) : null;
  const hasLatitude = latitude !== null;
  const hasLongitude = longitude !== null;

  if (hasLatitude !== hasLongitude) {
    issues.push("Standortkoordinaten bitte nur gemeinsam mit Breiten- und Laengengrad angeben.");
  }
  if (hasLatitude && (latitude < -90 || latitude > 90)) {
    issues.push("Der Breitengrad liegt ausserhalb des gueltigen Bereichs.");
  }
  if (hasLongitude && (longitude < -180 || longitude > 180)) {
    issues.push("Der Laengengrad liegt ausserhalb des gueltigen Bereichs.");
  }

  if (input.storage_profile?.has_storage) {
    const storagePower = hasValue(input.storage_profile.power_kw) ? readFiniteNumber(input.storage_profile.power_kw) : null;
    const storageEnergy = hasValue(input.storage_profile.energy_kwh) ? readFiniteNumber(input.storage_profile.energy_kwh) : null;
    if ((storagePower === null || storagePower <= 0) && (storageEnergy === null || storageEnergy <= 0)) {
      issues.push("Wenn ein Speicher aktiviert ist, bitte mindestens Leistung oder Energie sinnvoll angeben.");
    }
  }

  for (const [index, component] of (input.project_components ?? []).entries()) {
    const capacityKw = readFiniteNumber(component.capacity_kw);
    if (capacityKw === null || capacityKw <= 0) {
      issues.push(`Projektkomponente ${index + 1} braucht eine Leistung groesser als 0 kW.`);
      break;
    }
  }

  for (const [index, trafo] of (input.umspannwerk?.trafos ?? []).entries()) {
    const snMva = readFiniteNumber(trafo.sn_mva);
    if (snMva === null || snMva <= 0) {
      issues.push(`Trafo ${index + 1} im Umspannwerk braucht eine gueltige Nennleistung.`);
      break;
    }
  }

  if (input.n1_datengrundlage === "dso_verified") {
    const hasVerifiedBasis =
      hasValue(input.sk_min_mva) ||
      hasValue(input.trafo_sr_kva) ||
      hasValue(input.restkapazitaet_ms_mva) ||
      Boolean((input.umspannwerk?.trafos?.length ?? 0) > 0) ||
      Boolean((input.umspannwerk?.abgaenge?.length ?? 0) > 0);
    if (!hasVerifiedBasis) {
      issues.push("VNB-verifiziert darf nur mit konkreten Netz- oder Umspannwerksdaten verwendet werden.");
    }
  }

  if (issues.length > 0) {
    const [message, ...rest] = issues;
    throw new AnalyzeApiError(422, message, {
      code: "INPUT_VALIDATION",
      message,
      hint: rest.length > 0 ? rest.join(" ") : "Bitte Eingaben pruefen und erneut versuchen.",
    });
  }
}

function mapSpannungsebeneToKv(se: Spannungsebene): number {
  if (se === "NS") return 0.4;
  if (se === "MS") return 20;
  return 110;
}

function formatApiErrorMessage(status: number, detail: unknown) {
  if (Array.isArray(detail)) {
    const first = detail[0];
    const loc = Array.isArray((first as { loc?: unknown })?.loc) ? (first as { loc: unknown[] }).loc.join(".") : "";
    const msg = typeof (first as { msg?: unknown })?.msg === "string" ? String((first as { msg: string }).msg) : "Validierung";
    return `${msg}${loc ? ` (${loc})` : ""} [HTTP ${status}]`;
  }

  if (detail && typeof detail === "object") {
    const errorObject = detail as { fehler?: unknown; message?: unknown; hint?: unknown };
    if (Array.isArray(errorObject.fehler) && errorObject.fehler.length > 0) {
      return [String(errorObject.fehler[0]), typeof errorObject.hint === "string" ? errorObject.hint : null]
        .filter(Boolean)
        .join(" ");
    }
    if (typeof errorObject.message === "string") {
      return [errorObject.message, typeof errorObject.hint === "string" ? errorObject.hint : null]
        .filter(Boolean)
        .join(" ");
    }
  }

  if (status === 401) {
    return "Anmeldung erforderlich. Bitte einloggen und die Analyse erneut starten.";
  }

  if (typeof detail === "string") {
    return detail;
  }

  return `Analyse fehlgeschlagen (HTTP ${status})`;
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

function mapProjectComponentType(componentType: string): string {
  switch (componentType) {
    case "pv":
      return "PV";
    case "wind":
      return "WIND";
    case "battery":
      return "BESS";
    case "charging":
      return "CHARGING";
    case "heat_pump":
      return "HEAT_PUMP";
    case "electrolyzer":
      return "ELECTROLYZER";
    default:
      return componentType.toUpperCase();
  }
}

/** Backend optional numerics often use gt=0 — omit/zero/null would yield HTTP 422. */
function finitePositive(n: unknown): number | undefined {
  const x = Number(n);
  if (!Number.isFinite(x) || x <= 0) return undefined;
  return x;
}

function finiteNonNegative(n: unknown): number | undefined {
  const x = Number(n);
  if (!Number.isFinite(x) || x < 0) return undefined;
  return x;
}

function mapTopologieToBackend(topologie: GridCheckInput["topologie"]): string {
  if (topologie === "radial") return "stich";
  if (topologie === "ring") return "ring_offen";
  return topologie;
}

/** Missing distance gets a conservative default; invalid provided values are rejected earlier. */
function resolveEntfernungKm(n: unknown): number {
  if (!hasValue(n)) return 5;
  const x = Number(n);
  if (Number.isFinite(x) && x > 0 && x <= 500) return x;
  return 5;
}

/** Missing cos phi gets a conservative default; invalid provided values are rejected earlier. */
function resolveCosPhi(n: unknown): number {
  if (!hasValue(n)) return 0.95;
  const c = Number(n);
  if (Number.isFinite(c) && c >= 0.8 && c <= 1) return c;
  return 0.95;
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

function parseConfidenceLevel(raw: unknown): ConfidenceLevel {
  const level = String(raw ?? "D").toUpperCase();
  return level === "A" || level === "B" || level === "C" ? level : "D";
}

function toStringArray(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => String(item)).filter((item) => item.trim().length > 0);
}

function parseN1Bewertung(raw: unknown): GridCheckResult["n1_analyse"]["gesamt"]["bewertung"] {
  const value = String(raw ?? "NICHT_GEPRUEFT").toUpperCase();
  if (value === "GRUEN" || value === "GELB" || value === "ROT") return value;
  return "NICHT_GEPRUEFT";
}

function mapN1Component(raw: any): GridCheckResult["n1_analyse"]["n1_topologie"] {
  return {
    bewertung: parseN1Bewertung(raw?.bewertung),
    begruendung_technisch:
      typeof raw?.begruendung_technisch === "string" ? raw.begruendung_technisch : undefined,
    begruendung_klartext:
      typeof raw?.begruendung_klartext === "string" ? raw.begruendung_klartext : undefined,
    auslastung_n1_prozent:
      typeof raw?.auslastung_n1_prozent === "number" ? raw.auslastung_n1_prozent : null,
    engpass_trafo_idx:
      typeof raw?.engpass_trafo_idx === "number" ? raw.engpass_trafo_idx : undefined,
    iz_a: typeof raw?.iz_a === "number" ? raw.iz_a : null,
    i_n1_a: typeof raw?.i_n1_a === "number" ? raw.i_n1_a : null,
    primaer_abgang_label:
      typeof raw?.primaer_abgang_label === "string" ? raw.primaer_abgang_label : null,
    engpass_abgang_label:
      typeof raw?.engpass_abgang_label === "string" ? raw.engpass_abgang_label : null,
    abgaenge_gesamt: typeof raw?.abgaenge_gesamt === "number" ? raw.abgaenge_gesamt : undefined,
    abgaenge_auswertbar:
      typeof raw?.abgaenge_auswertbar === "number" ? raw.abgaenge_auswertbar : undefined,
    projektstrom_a: typeof raw?.projektstrom_a === "number" ? raw.projektstrom_a : null,
    beste_reserve_a: typeof raw?.beste_reserve_a === "number" ? raw.beste_reserve_a : null,
    reserve_ratio: typeof raw?.reserve_ratio === "number" ? raw.reserve_ratio : null,
    delta_u_n1_prozent:
      typeof raw?.delta_u_n1_prozent === "number" ? raw.delta_u_n1_prozent : null,
    grenze_prozent: typeof raw?.grenze_prozent === "number" ? raw.grenze_prozent : null,
  };
}

function mapN1Analysis(raw: any, fallbackN1: any): GridCheckResult["n1_analyse"] {
  const gesamt = raw?.gesamt ?? {};

  return {
    n1_topologie: mapN1Component(raw?.n1_topologie),
    n1_leitung: mapN1Component(raw?.n1_leitung),
    n1_abgang: mapN1Component(raw?.n1_abgang),
    n1_trafo: mapN1Component(raw?.n1_trafo),
    n1_spannung: mapN1Component(raw?.n1_spannung),
    gesamt: {
      bewertung: parseN1Bewertung(gesamt?.bewertung ?? fallbackN1?.bewertung),
      engpass_komponente:
        typeof gesamt?.engpass_komponente === "string"
          ? gesamt.engpass_komponente
          : typeof fallbackN1?.engpass_komponente === "string"
            ? fallbackN1.engpass_komponente
            : undefined,
      n1_klasse:
        typeof gesamt?.n1_klasse === "string"
          ? gesamt.n1_klasse
          : typeof fallbackN1?.n1_klasse === "string"
            ? fallbackN1.n1_klasse
            : undefined,
      konfidenz:
        typeof gesamt?.konfidenz === "number"
          ? gesamt.konfidenz
          : typeof fallbackN1?.n1_konfidenz === "number"
            ? fallbackN1.n1_konfidenz
            : undefined,
      stufenbegruendung:
        typeof gesamt?.stufenbegruendung === "string"
          ? gesamt.stufenbegruendung
          : typeof fallbackN1?.stufenbegruendung === "string"
            ? fallbackN1.stufenbegruendung
            : undefined,
      dso_daten_vorhanden:
        typeof gesamt?.dso_daten_vorhanden === "boolean"
          ? gesamt.dso_daten_vorhanden
          : typeof fallbackN1?.dso_daten_vorhanden === "boolean"
            ? fallbackN1.dso_daten_vorhanden
            : undefined,
      empfehlungen: toStringArray(gesamt?.empfehlungen ?? fallbackN1?.detail_empfehlungen),
      nachweise_vorhanden: toStringArray(gesamt?.nachweise_vorhanden ?? fallbackN1?.nachweise_vorhanden),
      nachweise_fehlend: toStringArray(gesamt?.nachweise_fehlend ?? fallbackN1?.nachweise_fehlend),
    },
    annahmen: Array.isArray(raw?.annahmen)
      ? raw.annahmen.map((item: any) => ({
          feld: typeof item?.feld === "string" ? item.feld : undefined,
          wert: item?.wert,
          quelle: typeof item?.quelle === "string" ? item.quelle : undefined,
          begruendung: typeof item?.begruendung === "string" ? item.begruendung : undefined,
        }))
      : [],
    berechnungs_version:
      typeof raw?.berechnungs_version === "string" ? raw.berechnungs_version : undefined,
    backend: typeof raw?.backend === "string" ? raw.backend : undefined,
  };
}

function mapResponseToUi(res: any, input: GridCheckInput): GridCheckResult {
  const szenarien = toUiSzenarien(res?.szenarien);
  const worst = pickWorstCase(szenarien);
  const score = Number(res?.scores?.gesamt ?? 0);
  const investition = Number(res?.kosten?.investition_gesamt_eur ?? 0);
  const dq = parseConfidenceLevel(res?.datenqualitaet?.klasse);
  const projektprofil = res?.projektprofil ?? {};
  const speicherBewertung = res?.speicher_bewertung ?? {};
  const routeEnvironment = res?.route_environment ?? {};
  const stakeholderBewertung = res?.stakeholder_bewertung ?? {};
  const transparenz = res?.transparenz ?? {};
  const ki = res?.ki ?? {};
  const kiKalibrierung = ki?.kalibrierung ?? {};
  const kiFeedbackLoop = ki?.feedback_loop ?? {};
  const kiAnomalie = ki?.anomalie_check ?? {};
  const revision = res?.revision ?? {};
  const billingAccess = res?.billing_access ?? {};
  const history = res?.history ?? {};
  const n1 = res?.n1 ?? {};
  const n1Analyse = mapN1Analysis(res?.n1_analyse, n1);
  const kosten = res?.kosten ?? {};

  const harteVerstoesse = Array.isArray(res?.scores?.harte_verstoesse)
    ? (res.scores.harte_verstoesse as string[])
    : [];
  const weicheHinweise = Array.isArray(res?.scores?.weiche_hinweise)
    ? (res.scores.weiche_hinweise as string[])
    : [];
  const einschraenkungen = [
    ...(Array.isArray(res?.warnungen) ? res.warnungen : []),
    ...harteVerstoesse,
    ...weicheHinweise,
  ];

  return {
    machbar: String(res?.fazit?.entscheidung ?? "C") !== "C",
    machbarkeit_stufe: mapFazitToStufe(res?.fazit?.entscheidung),
    einschraenkungen,
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
    n1_prescreen_ok: typeof n1?.n1_sicher === "boolean" ? n1.n1_sicher : null,
    n1_prescreen_detail: String(n1?.detail_text ?? n1?.topologie_text ?? ""),
    n1_hinweis: String(n1?.stufenbegruendung ?? n1?.leitung_text ?? ""),
    n1: {
      n1_sicher: typeof n1?.n1_sicher === "boolean" ? n1.n1_sicher : null,
      bewertung: parseN1Bewertung(n1?.bewertung),
      topologie: typeof n1?.topologie === "string" ? n1.topologie : undefined,
      topologie_text: String(n1?.topologie_text ?? ""),
      leitung_n1: typeof n1?.leitung_n1 === "boolean" ? n1.leitung_n1 : null,
      leitung_text: typeof n1?.leitung_text === "string" ? n1.leitung_text : undefined,
      n1_auslastung_prozent:
        typeof n1?.n1_auslastung_prozent === "number" ? n1.n1_auslastung_prozent : null,
      trafo_n1: typeof n1?.trafo_n1 === "boolean" ? n1.trafo_n1 : null,
      detail_text: typeof n1?.detail_text === "string" ? n1.detail_text : undefined,
      n1_klasse: typeof n1?.n1_klasse === "string" ? n1.n1_klasse : undefined,
      n1_konfidenz: typeof n1?.n1_konfidenz === "number" ? n1.n1_konfidenz : undefined,
      engpass_komponente:
        typeof n1?.engpass_komponente === "string" ? n1.engpass_komponente : undefined,
      stufenbegruendung:
        typeof n1?.stufenbegruendung === "string" ? n1.stufenbegruendung : undefined,
      nachweise_vorhanden: toStringArray(n1?.nachweise_vorhanden),
      nachweise_fehlend: toStringArray(n1?.nachweise_fehlend),
      dso_daten_vorhanden:
        typeof n1?.dso_daten_vorhanden === "boolean" ? n1.dso_daten_vorhanden : undefined,
      detail_empfehlungen: toStringArray(n1?.detail_empfehlungen),
      detail_annahmen: toStringArray(n1?.detail_annahmen),
    },
    n1_analyse: n1Analyse,
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
    kosten_bandbreite:
      typeof kosten?.band_basis_eur === "number" || typeof kosten?.investition_gesamt_eur === "number"
        ? {
            niedrig_eur: Number(kosten?.band_niedrig_eur ?? kosten?.investition_gesamt_eur ?? investition),
            basis_eur: Number(kosten?.band_basis_eur ?? kosten?.investition_gesamt_eur ?? investition),
            hoch_eur: Number(kosten?.band_hoch_eur ?? kosten?.investition_gesamt_eur ?? investition),
            confidence_pct: typeof kosten?.konfidenz_prozent === "number" ? kosten.konfidenz_prozent : undefined,
            source: typeof kosten?.quelle === "string" ? kosten.quelle : undefined,
            assumptions: Array.isArray(kosten?.band_annahmen)
              ? kosten.band_annahmen.map((item: unknown) => String(item))
              : [],
            drivers: Array.isArray(kosten?.hauptrisikotreiber)
              ? kosten.hauptrisikotreiber.map((item: unknown) => String(item))
              : [],
          }
        : undefined,
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
    erweiterte_scores: {
      netzdienlichkeit: Number(res?.erweiterte_scores?.netzdienlichkeit ?? 0),
      projektfit: Number(res?.erweiterte_scores?.projektfit ?? 0),
      umwelt_trasse: Number(res?.erweiterte_scores?.umwelt_trasse ?? 0),
      stakeholder_fit: Number(res?.erweiterte_scores?.stakeholder_fit ?? 0),
    },
    score,
    konfidenz: Number(res?.ki?.konfidenz_prozent ?? 0),
    daten_confidence: dq,
    z_quelle_ohm: Number(res?.impedanz?.r_q ?? 0),
    z_trafo_ohm: Number(res?.impedanz?.r_t ?? 0),
    z_leitung_ohm: Number(res?.impedanz?.r_l ?? 0),
    z_gesamt_ohm: Number(res?.impedanz?.z_ges ?? 0),
    projektprofil: {
      total_installed_kw: Number(projektprofil?.total_installed_kw ?? input.anschlussleistung_kw),
      component_count: Number(projektprofil?.component_count ?? input.project_components?.length ?? 1),
      is_hybrid: Boolean(projektprofil?.is_hybrid),
      component_summary: Array.isArray(projektprofil?.component_summary)
        ? projektprofil.component_summary.map((item: unknown) => String(item))
        : [],
      max_export_kw: Number(projektprofil?.max_export_kw ?? input.netzanschlusspunkt?.max_export_kw ?? input.anschlussleistung_kw),
      max_import_kw: Number(projektprofil?.max_import_kw ?? input.netzanschlusspunkt?.max_import_kw ?? 0),
      summary: String(projektprofil?.summary ?? ""),
    },
    speicher_bewertung: {
      relevant: Boolean(speicherBewertung?.relevant),
      operation_mode: (String(speicherBewertung?.operation_mode ?? "unknown") as GridCheckResult["speicher_bewertung"]["operation_mode"]),
      flexibility_score: Number(speicherBewertung?.flexibility_score ?? 0),
      grid_support_score: Number(speicherBewertung?.grid_support_score ?? 0),
      benefit_flags: Array.isArray(speicherBewertung?.benefit_flags)
        ? speicherBewertung.benefit_flags.map((item: unknown) => String(item))
        : [],
      warnings: Array.isArray(speicherBewertung?.warnings)
        ? speicherBewertung.warnings.map((item: unknown) => String(item))
        : [],
      summary: String(speicherBewertung?.summary ?? ""),
      disclaimer: String(speicherBewertung?.disclaimer ?? ""),
    },
    route_environment: {
      risk_score: Number(routeEnvironment?.risk_score ?? 0),
      risk_level: (String(routeEnvironment?.risk_level ?? "mittel") as GridCheckResult["route_environment"]["risk_level"]),
      drivers: Array.isArray(routeEnvironment?.drivers)
        ? routeEnvironment.drivers.map((item: unknown) => String(item))
        : [],
      mitigation: Array.isArray(routeEnvironment?.mitigation)
        ? routeEnvironment.mitigation.map((item: unknown) => String(item))
        : [],
      summary: String(routeEnvironment?.summary ?? ""),
    },
    stakeholder_bewertung: {
      netzbetreiber_score: Number(stakeholderBewertung?.netzbetreiber_score ?? 0),
      projektierer_score: Number(stakeholderBewertung?.projektierer_score ?? 0),
      umsetzung_score: Number(stakeholderBewertung?.umsetzung_score ?? 0),
      konflikt_level: (String(stakeholderBewertung?.konflikt_level ?? "mittel") as GridCheckResult["stakeholder_bewertung"]["konflikt_level"]),
      konflikt_summary: String(stakeholderBewertung?.konflikt_summary ?? ""),
      recommended_focus: String(stakeholderBewertung?.recommended_focus ?? ""),
    },
    transparenz: {
      assumptions: Array.isArray(transparenz?.assumptions)
        ? transparenz.assumptions.map((item: unknown) => String(item))
        : [],
      disclaimers: Array.isArray(transparenz?.disclaimers)
        ? transparenz.disclaimers.map((item: unknown) => String(item))
        : [],
      confidence_notes: Array.isArray(transparenz?.confidence_notes)
        ? transparenz.confidence_notes.map((item: unknown) => String(item))
        : [],
    },
    ki: {
      konfidenz: Number(ki?.konfidenz ?? Number(ki?.konfidenz_prozent ?? 0) / 100),
      konfidenz_prozent: Number(ki?.konfidenz_prozent ?? 0),
      aehnliche_faelle: Number(ki?.aehnliche_faelle ?? 0),
      kalibrierung: {
        samples: Number(kiKalibrierung?.samples ?? 0),
        trefferquote: Number(kiKalibrierung?.trefferquote ?? 0),
        durchschnittlicher_fehler: Number(kiKalibrierung?.durchschnittlicher_fehler ?? 0),
        bias: Number(kiKalibrierung?.bias ?? 0),
        kalibrierungsfaktor: Number(kiKalibrierung?.kalibrierungsfaktor ?? 1),
        bestaetigungsquote: Number(kiKalibrierung?.bestaetigungsquote ?? 0),
        status: String(kiKalibrierung?.status ?? "NO_FEEDBACK"),
      },
      feedback_loop: {
        samples_total: Number(kiFeedbackLoop?.samples_total ?? 0),
        linked_samples: Number(kiFeedbackLoop?.linked_samples ?? 0),
        bestaetigt: Number(kiFeedbackLoop?.bestaetigt ?? 0),
        korrigiert: Number(kiFeedbackLoop?.korrigiert ?? 0),
        bestaetigungsquote: Number(kiFeedbackLoop?.bestaetigungsquote ?? 0),
        coverage_ratio: Number(kiFeedbackLoop?.coverage_ratio ?? 0),
        anomaly_feedbacks: Number(kiFeedbackLoop?.anomaly_feedbacks ?? 0),
        status: String(kiFeedbackLoop?.status ?? "NO_FEEDBACK"),
        last_feedback_at:
          typeof kiFeedbackLoop?.last_feedback_at === "string" ? kiFeedbackLoop.last_feedback_at : null,
      },
      anomalie_check: {
        is_anomaly: Boolean(kiAnomalie?.is_anomaly),
        severity: (String(kiAnomalie?.severity ?? "niedrig") as GridCheckResult["ki"]["anomalie_check"]["severity"]),
        score: Number(kiAnomalie?.score ?? 0),
        flags: Array.isArray(kiAnomalie?.flags) ? kiAnomalie.flags.map((item: unknown) => String(item)) : [],
        summary: String(kiAnomalie?.summary ?? ""),
      },
      hinweise: Array.isArray(ki?.hinweise) ? ki.hinweise.map((item: unknown) => String(item)) : [],
    },
    revision: {
      revisionsnummer: Number(revision?.revisionsnummer ?? 0) || undefined,
      uuid: typeof revision?.uuid === "string" ? revision.uuid : undefined,
      timestamp: typeof revision?.timestamp === "string" ? revision.timestamp : undefined,
      schema_version: typeof revision?.schema_version === "string" ? revision.schema_version : undefined,
      engine_version: typeof revision?.engine_version === "string" ? revision.engine_version : undefined,
      previous_hash: typeof revision?.previous_hash === "string" ? revision.previous_hash : undefined,
      hash: typeof revision?.hash === "string" ? revision.hash : undefined,
      dry_run: typeof revision?.dry_run === "boolean" ? revision.dry_run : undefined,
      fehler: typeof revision?.fehler === "string" ? revision.fehler : undefined,
    },
    billing_access: {
      offer_id: typeof billingAccess?.offer_id === "string" ? billingAccess.offer_id : undefined,
      package_scope: typeof billingAccess?.package_scope === "string" ? billingAccess.package_scope : undefined,
      usage_bucket: typeof billingAccess?.usage_bucket === "string" ? billingAccess.usage_bucket : undefined,
      report_scope: typeof billingAccess?.report_scope === "string" ? billingAccess.report_scope : undefined,
      ops_followup_required:
        typeof billingAccess?.ops_followup_required === "boolean" ? billingAccess.ops_followup_required : undefined,
    },
    history: {
      analysis_run_id: Number(history?.analysis_run_id ?? 0) || undefined,
    },
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

export function buildAnalyzePayload(input: GridCheckInput): Record<string, unknown> {
  const pMw = finitePositive(input.anschlussleistung_kw);
  const leistung_mw = pMw !== undefined ? pMw / 1000 : 0.001;
  const backendTopologie = mapTopologieToBackend(input.topologie);

  const payload: Record<string, unknown> = {
    nennspannung: mapSpannungsebeneToKv(input.spannungsebene),
    leistung_mw,
    leitungstyp: (input.kabeltyp?.trim() || "NA2XS2Y240"),
    entfernung_km: resolveEntfernungKm(input.entfernung_km),
    anschlussart: mapRichtung(input.richtung),
    anlagentyp: mapAnlagentyp(input.anlagentyp),
    plz: input.plz?.trim() || undefined,
    ort: input.ort?.trim() || undefined,
    standort: input.project_location?.address_hint?.trim() || input.ort?.trim() || undefined,
    antragsteller: input.antragsteller?.trim() || undefined,
    projektreife: input.projektreife ?? undefined,
    foerderfrist: input.foerderfrist ?? undefined,
    baugenehmigung_vorhanden: input.baugenehmigung_vorhanden ?? false,
    cos_phi: resolveCosPhi(input.cos_phi),
    parallele_systeme: 1,
    redundanz: backendTopologie !== "stich" && backendTopologie !== "unbekannt",
    p_kw: finitePositive(input.anschlussleistung_kw),
    bestehende_einspeisung_mw: 0,
    temperatur_c: 20,
    topologie: backendTopologie,
    restkapazitaet_ms_mva: finitePositive(input.restkapazitaet_ms_mva),
    umschaltzeit_min: finiteNonNegative(input.umschaltzeit_min),
    n1_datengrundlage: input.n1_datengrundlage ?? "unknown",
  };

  const sk = finitePositive(input.sk_min_mva);
  if (sk !== undefined) payload.sk_mva = sk;

  const trafoKva = finitePositive(input.trafo_sr_kva);
  if (trafoKva !== undefined) payload.trafo_s_mva = trafoKva / 1000;

  const uk = finitePositive(input.trafo_uk_pct);
  if (uk !== undefined) payload.uk_prozent = uk;

  if (
    input.vorbelastung_pct !== undefined &&
    Number.isFinite(input.vorbelastung_pct) &&
    input.vorbelastung_pct >= 0 &&
    input.vorbelastung_pct <= 100
  ) {
    payload.bestand_auslastung_prozent = input.vorbelastung_pct;
  }

  if (Array.isArray(input.project_components) && input.project_components.length > 0) {
    payload.project_components = input.project_components.map((component) => ({
      component_type: component.component_type,
      label: component.label?.trim() || mapProjectComponentType(component.component_type),
      capacity_kw: component.capacity_kw,
      energy_kwh: finitePositive(component.energy_kwh),
      max_export_kw: component.max_export_kw ?? undefined,
      max_import_kw: component.max_import_kw ?? undefined,
      controllable: component.controllable ?? false,
    }));
  }

  if (input.netzanschlusspunkt) {
    payload.netzanschlusspunkt = {
      max_export_kw: input.netzanschlusspunkt.max_export_kw ?? undefined,
      max_import_kw: input.netzanschlusspunkt.max_import_kw ?? undefined,
      export_limit_mode: input.netzanschlusspunkt.export_limit_mode ?? "none",
      own_transformer: input.netzanschlusspunkt.own_transformer ?? false,
      own_substation: input.netzanschlusspunkt.own_substation ?? false,
      own_switchgear: input.netzanschlusspunkt.own_switchgear ?? false,
      remote_metering_ready: input.netzanschlusspunkt.remote_metering_ready ?? false,
      preferred_connection_note: input.netzanschlusspunkt.preferred_connection_note?.trim() || undefined,
    };
  }

  if (input.storage_profile) {
    payload.storage_profile = {
      has_storage: input.storage_profile.has_storage ?? false,
      operation_mode: input.storage_profile.operation_mode ?? "unknown",
      power_kw: input.storage_profile.power_kw ?? undefined,
      energy_kwh: input.storage_profile.energy_kwh ?? undefined,
      grid_support_services: input.storage_profile.grid_support_services ?? [],
      reactive_power_capable: input.storage_profile.reactive_power_capable ?? false,
      remote_control_capable: input.storage_profile.remote_control_capable ?? false,
      schedule_based_dispatch: input.storage_profile.schedule_based_dispatch ?? false,
      dynamic_export_limit: input.storage_profile.dynamic_export_limit ?? false,
      peak_shaving: input.storage_profile.peak_shaving ?? false,
      curtailment_ready: input.storage_profile.curtailment_ready ?? false,
      notes: input.storage_profile.notes?.trim() || undefined,
    };
  }

  if (input.environmental_route) {
    payload.environmental_route = {
      route_length_km: input.environmental_route.route_length_km ?? undefined,
      crossings_count: input.environmental_route.crossings_count ?? undefined,
      protected_area_touch: input.environmental_route.protected_area_touch ?? false,
      water_protection_area: input.environmental_route.water_protection_area ?? false,
      forest_crossing: input.environmental_route.forest_crossing ?? false,
      third_party_land: input.environmental_route.third_party_land ?? false,
      noise_sensitive_area: input.environmental_route.noise_sensitive_area ?? false,
      route_complexity: input.environmental_route.route_complexity ?? "unbekannt",
      mitigation_measures: input.environmental_route.mitigation_measures ?? [],
      notes: input.environmental_route.notes?.trim() || undefined,
    };
  }

  if (input.stakeholder_context) {
    const resolvedCustomerType = input.stakeholder_context.customer_type ?? undefined;
    payload.stakeholder_context = {
      customer_type: resolvedCustomerType,
      priority_focus: input.stakeholder_context.priority_focus ?? "balanced",
      investor_relevant:
        input.stakeholder_context.investor_relevant ?? resolvedCustomerType === "investor",
      netzbetreiber_dialog_needed: input.stakeholder_context.netzbetreiber_dialog_needed ?? false,
    };
  }

  if (input.project_location) {
    payload.project_location = {
      latitude: input.project_location.latitude ?? undefined,
      longitude: input.project_location.longitude ?? undefined,
      address_hint: input.project_location.address_hint?.trim() || undefined,
      area_radius_m: input.project_location.area_radius_m ?? undefined,
    };
  }

  if (input.umspannwerk) {
    payload.umspannwerk = {
      datenquelle: input.umspannwerk.datenquelle ?? input.n1_datengrundlage ?? "unknown",
      trafos: (input.umspannwerk.trafos ?? [])
        .map((trafo) => ({
          label: trafo.label?.trim() || undefined,
          sn_mva: finitePositive(trafo.sn_mva),
          belastung_aktuell_mw: finiteNonNegative(trafo.belastung_aktuell_mw),
        }))
        .filter((trafo) => typeof trafo.sn_mva === "number"),
      abgaenge: (input.umspannwerk.abgaenge ?? []).map((abgang) => ({
        label: abgang.label?.trim() || undefined,
        i_max_a: finitePositive(abgang.i_max_a),
        belastung_aktuell_a: finiteNonNegative(abgang.belastung_aktuell_a),
        reserve_n1_a: finiteNonNegative(abgang.reserve_n1_a),
        reserve_i_a: finiteNonNegative(abgang.reserve_i_a),
        primary: abgang.primary ?? false,
        verfuegbar_im_n1: abgang.verfuegbar_im_n1 ?? true,
        koppelbar: abgang.koppelbar ?? true,
        datenquelle: abgang.datenquelle ?? input.n1_datengrundlage ?? "unknown",
      })),
    };
  }
  return payload;
}

export async function analyzeGridcheck(
  input: GridCheckInput,
  options?: { projectId?: number; requestedOfferId?: string }
): Promise<GridCheckResult> {
  validateAnalyzeInput(input);
  const csrf = getCsrfTokenFromCookie();
  const payload = buildAnalyzePayload(input);
  if (options?.projectId) {
    payload.project_id = options.projectId;
  }
  if (options?.requestedOfferId) {
    payload.requested_offer_id = options.requestedOfferId;
  }
  let res: Response;
  try {
    res = await fetch(`${BASE}/analyze`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...bearerAuthHeaders(),
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new AnalyzeApiError(
      0,
      "Backend nicht erreichbar. Bitte pruefen, ob Backend (Port 8000) und NEXT_PUBLIC_API_BASE (/api/backend) erreichbar sind.",
      null,
    );
  }

  let body: any = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  if (!res.ok) {
    const detail = body?.detail;
    const msg = formatApiErrorMessage(res.status, detail);
    throw new AnalyzeApiError(
      res.status,
      msg,
      detail && typeof detail === "object" && !Array.isArray(detail) ? detail : null,
    );
  }

  return mapResponseToUi(body, input);
}

export async function exportStakeholderPdf(
  input: GridCheckInput,
  stakeholder: "projektierer" | "vnb" | "invest" = "projektierer",
  options?: { requestedOfferId?: string }
): Promise<Blob> {
  validateAnalyzeInput(input);
  const csrf = getCsrfTokenFromCookie();
  const payload = buildAnalyzePayload(input);
  if (options?.requestedOfferId) {
    payload.requested_offer_id = options.requestedOfferId;
  }
  const res = await fetch(`${REPORT_BASE}/${stakeholder}?format=pdf`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/pdf",
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify({ analyze_request: payload }),
  });
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    throw new AnalyzeApiError(
      res.status,
      formatApiErrorMessage(res.status, (body as { detail?: unknown } | null)?.detail),
      ((body as { detail?: unknown } | null)?.detail &&
      typeof (body as { detail?: unknown }).detail === "object" &&
      !Array.isArray((body as { detail?: unknown }).detail)
        ? ((body as { detail?: ApiErrorDetail }).detail ?? null)
        : null)
    );
  }
  return res.blob();
}
