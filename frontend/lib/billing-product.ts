import type { BillingOffer } from "@/lib/api/billing";
import type { GridCheckInput } from "@/types";

export type OfferProfile = {
  title: string;
  badge: string;
  audience: string;
  deliverable: string;
  boundary: string;
  nextStep: string;
};

const OFFER_PROFILES: Record<string, OfferProfile> = {
  free: {
    title: "Free Check",
    badge: "Basis-Check",
    audience: "Zum ersten Screening eines Standorts oder einer neuen Opportunity.",
    deliverable: "Kompakter Basis-Run mit frueher Machbarkeits- und Risikoindikation.",
    boundary: "Hybrid-, Speicher- und Trassenlogik bleiben im Free-/Basic-Scope bewusst begrenzt.",
    nextStep: "Bei belastbarerem Projektbedarf auf Premium, Professional oder Pro wechseln.",
  },
  basic_schnellcheck: {
    title: "Basic Schnellcheck",
    badge: "Basis-Report",
    audience: "Fuer einzelne Vorhaben vor Antrag und Detailplanung.",
    deliverable: "Kompakter Basis-Report fuer schnelle Anschlussklarheit ohne Vertiefung.",
    boundary: "Mehrkomponenten-, Speicher- und Umwelt-/Trassensicht sind noch nicht Teil des Scopes.",
    nextStep: "Bei strategischem Bedarf auf Premium oder Professional erweitern.",
  },
  premium_pre_check: {
    title: "Premium Pre-Check",
    badge: "Premium-Report",
    audience: "Fuer Vorhaben mit Investoren-, Pipeline- oder Freigabe-Druck.",
    deliverable: "Vertiefter Self-Serve-Report mit Hybrid-, Speicher- und Trassenperspektive.",
    boundary: "Professional-Follow-up und manuell betreute Anschlussstrategie sind noch nicht enthalten.",
    nextStep: "Bei noetiger Anschlussstrategie oder abgestimmter Nacharbeit Professional dazu waehlen.",
  },
  professional_anschlussstrategie: {
    title: "Professional Anschlussstrategie",
    badge: "Servicepfad",
    audience: "Fuer kritische Projekte vor Antrag, EPC-Start oder IC-/Board-Freigabe.",
    deliverable: "Professional-Reportscope plus operativer Follow-up fuer Anschlussstrategie und Visualisierung.",
    boundary: "Professional ist kein Express-SLA und kein VNB-Pilotprogramm.",
    nextStep: "Nach dem Run folgt ein sichtbarer operativer Nachlauf statt eines stillen Self-Serve-Abschlusses.",
  },
  pro_lizenz: {
    title: "Pro Lizenz",
    badge: "SaaS-Lizenz",
    audience: "Fuer Teams mit laufender Projektpipeline und wiederkehrenden Checks.",
    deliverable: "Fortlaufende Premium-Tiefe im Self-Serve-Modus mit Inklusiv-Analysen pro Periode.",
    boundary: "Professional-Follow-up und Express bleiben separate Servicepfade.",
    nextStep: "Ideal fuer wiederkehrende Vorqualifizierung, nicht als Ersatz fuer Professional-Einzelfaelle.",
  },
  vnb_pilot: {
    title: "VNB Pilot",
    badge: "Pilotpfad",
    audience: "Fuer Netzbetreiber-nahe Zusammenarbeit, Pilotierung und Prozessabstimmung.",
    deliverable: "Abgestimmter Pilot- und Servicepfad statt sofortiger Self-Serve-Buchung.",
    boundary: "Kein Standard-Checkout und keine versteckte Zusatzoption hinter Premium oder Pro.",
    nextStep: "Kontaktaufnahme und gemeinsames Rollout-/Pilot-Setup mit GridCheck.",
  },
  express_upgrade: {
    title: "Express",
    badge: "Add-on",
    audience: "Fuer zeitkritische Vorhaben mit externer Termin- oder Gremienlogik.",
    deliverable: "Operativer Beschleunigungspfad fuer Bearbeitung und Abstimmung.",
    boundary: "Express veraendert nicht automatisch Analyseumfang, Reportscope oder technische Tiefe.",
    nextStep: "Nur in Kombination mit passendem Analysepaket sinnvoll.",
  },
};

const SCOPE_LABELS: Record<string, string> = {
  basic: "Basis-Scope",
  premium: "Premium-Scope",
  professional: "Professional-Scope",
  pilot: "Pilot-Scope",
  addon: "Add-on",
};

const REPORT_SCOPE_LABELS: Record<string, string> = {
  none: "Kein zusaetzlicher Report",
  basic: "Basis-Report",
  premium: "Premium-Report",
  professional: "Professional-Report",
};

export function getOfferDisplayName(offerId?: string | null) {
  if (!offerId) return "Analysepaket";
  return OFFER_PROFILES[offerId]?.title ?? offerId;
}

export function getPackageScopeLabel(packageScope?: string | null) {
  if (!packageScope) return "Scope offen";
  return SCOPE_LABELS[packageScope] ?? packageScope;
}

export function getReportScopeLabel(reportScope?: string | null) {
  if (!reportScope) return "Reportscope offen";
  return REPORT_SCOPE_LABELS[reportScope] ?? reportScope;
}

export function getOfferProfile(offerId?: string | null, packageScope?: string | null): OfferProfile {
  if (offerId && OFFER_PROFILES[offerId]) {
    return OFFER_PROFILES[offerId];
  }
  if (packageScope === "basic") {
    return OFFER_PROFILES.basic_schnellcheck;
  }
  if (packageScope === "premium") {
    return OFFER_PROFILES.premium_pre_check;
  }
  if (packageScope === "professional") {
    return OFFER_PROFILES.professional_anschlussstrategie;
  }
  if (packageScope === "pilot") {
    return OFFER_PROFILES.vnb_pilot;
  }
  return {
    title: "Analysepaket",
    badge: "Scope",
    audience: "Fuer einen sauberen, kontobezogenen Analyse-Run.",
    deliverable: "Die Analyse wird mit dem aktuell verfuegbaren Paketkontext gespeichert.",
    boundary: "Scope, Reporttiefe und Folgepfade richten sich nach dem aktiven Paket.",
    nextStep: "Bei hoeherem Bedarf einen passenderen Produktpfad waehlen.",
  };
}

export function getPackageBoundaryWarnings(
  input: Partial<GridCheckInput> | null | undefined,
  packageScope?: string | null,
) {
  if (!input || packageScope !== "basic") {
    return [];
  }

  const warnings: string[] = [];
  if (Array.isArray(input.project_components) && input.project_components.length > 1) {
    warnings.push("Mehrkomponenten- und Hybridlogik wird im Basis-Scope auf einen Kernfall reduziert.");
  }
  if (input.storage_profile?.has_storage || input.storage_profile?.power_kw || input.storage_profile?.energy_kwh) {
    warnings.push("Speicher- und Netzdienlichkeitsbewertung ist erst ab Premium oder Pro sichtbar.");
  }
  if (
    input.environmental_route?.route_length_km ||
    input.environmental_route?.crossings_count ||
    input.environmental_route?.protected_area_touch ||
    input.environmental_route?.water_protection_area ||
    input.environmental_route?.forest_crossing ||
    input.environmental_route?.third_party_land ||
    input.environmental_route?.noise_sensitive_area
  ) {
    warnings.push("Umwelt-, Trassen- und Genehmigungsrisiken werden erst ab Premium oder Pro ausgewiesen.");
  }
  return warnings;
}

export function findOfferById(
  offers: BillingOffer[] | undefined,
  addons: BillingOffer[] | undefined,
  offerId?: string | null,
) {
  if (!offerId) return null;
  return [...(offers ?? []), ...(addons ?? [])].find((offer) => offer.offer_id === offerId) ?? null;
}
