export type PurchaseIntent =
  | "general"
  | "upgrade"
  | "pro"
  | "professional"
  | "express"
  | "vnb-pilot";

export type PurchaseIntentProfile = {
  id: PurchaseIntent;
  label: string;
  shortLabel: string;
  badge: string;
  audience: string;
  summary: string;
  subject: string;
  suggestedMessage: string;
  nextStep: string;
};

const INTENT_PROFILES: Record<PurchaseIntent, PurchaseIntentProfile> = {
  general: {
    id: "general",
    label: "Allgemeine Anfrage",
    shortLabel: "Allgemein",
    badge: "Kontakt",
    audience: "Fuer allgemeine Produktfragen, Demo-Wuensche oder offene Kaufpfade.",
    summary: "Geeignet, wenn noch nicht klar ist, ob Self-Serve, Pro, Professional oder Pilot der richtige Pfad ist.",
    subject: "Allgemeine GridCheck Anfrage",
    suggestedMessage:
      "Wir moechten GridCheck besser einordnen. Bitte melden Sie sich mit einer kurzen Produktempfehlung fuer unseren Einsatzfall.",
    nextStep: "Wir beantworten den passenden Produktpfad auf Basis Ihres Einsatzfalls.",
  },
  upgrade: {
    id: "upgrade",
    label: "Upgrade fuer weitere Analysen",
    shortLabel: "Upgrade",
    badge: "Self-Serve",
    audience: "Fuer Teams, die nach Free Checks oder ersten Tests den passenden Upgrade-Pfad suchen.",
    summary: "Fokussiert auf die Frage, ob Basic, Premium, Professional oder Pro den richtigen naechsten Schritt bildet.",
    subject: "Upgradeberatung fuer GridCheck",
    suggestedMessage:
      "Wir haben die ersten Checks genutzt und moechten jetzt den passenden Upgrade-Pfad fuer weitere Analysen abstimmen.",
    nextStep: "Wir helfen bei der Einordnung zwischen Einzelprojektpaket, laufender Pro Nutzung und betreutem Servicepfad.",
  },
  pro: {
    id: "pro",
    label: "Pro Lizenz fuer laufende Pipeline",
    shortLabel: "Pro",
    badge: "SaaS",
    audience: "Fuer wiederkehrende Vorqualifizierung ueber mehrere Projekte und Teamkontexte.",
    summary: "Der passende Pfad fuer laufende Projektpipelines mit wiederkehrenden Self-Serve-Checks.",
    subject: "Interesse an GridCheck Pro Lizenz",
    suggestedMessage:
      "Wir pruefen eine laufende GridCheck Nutzung fuer mehrere Projekte und moechten Umfang, Teamnutzung und Einfuehrung abstimmen.",
    nextStep: "Naechster Schritt ist die Einordnung von Teamgroesse, Pipelinevolumen und passendem Rollout.",
  },
  professional: {
    id: "professional",
    label: "Professional Anschlussstrategie",
    shortLabel: "Professional",
    badge: "Servicepfad",
    audience: "Fuer kritische Einzelvorhaben vor Antrag, EPC-Start, IC- oder Board-Freigabe.",
    summary: "Professional ist die betreute Anschlussstrategie mit operativem Follow-up, nicht nur ein tieferer Self-Serve-Run.",
    subject: "Anfrage Professional Anschlussstrategie",
    suggestedMessage:
      "Wir haben ein kritisches Vorhaben und moechten die Professional Anschlussstrategie inklusive naechster Schritte und operativem Follow-up abstimmen.",
    nextStep: "Bitte Projektphase, Zeitdruck und Grund fuer die strategische Vertiefung kurz mitgeben.",
  },
  express: {
    id: "express",
    label: "Express Zusatzpfad",
    shortLabel: "Express",
    badge: "Add-on",
    audience: "Fuer zeitkritische Vorhaben mit enger Terminlage oder Gremien-/IC-Druck.",
    summary: "Express ist ein Zeit- und Bearbeitungspfad, kein verstecktes Upgrade des technischen Analyseumfangs.",
    subject: "Anfrage Express Zusatzpfad",
    suggestedMessage:
      "Wir haben einen zeitkritischen Fall und moechten pruefen, ob der Express Zusatzpfad fuer unseren Zeitplan sinnvoll ist.",
    nextStep: "Bitte Frist, Entscheidungsdatum und bestehendes Analysepaket angeben.",
  },
  "vnb-pilot": {
    id: "vnb-pilot",
    label: "VNB Pilot / abgestimmter Rollout",
    shortLabel: "VNB Pilot",
    badge: "Pilotpfad",
    audience: "Fuer Netzbetreiber-nahe Pilotierung, Prozessabstimmung und abgestimmte Einfuehrung.",
    summary: "VNB Pilot ist bewusst kein Self-Serve-Checkout, sondern ein gemeinsamer Pilot- und Servicepfad.",
    subject: "Anfrage VNB Pilot",
    suggestedMessage:
      "Wir moechten einen VNB-nahen Pilot oder einen abgestimmten Rollout mit GridCheck besprechen.",
    nextStep: "Bitte Rolle, Zielbild, Pilotumfang und beteiligte Bereiche kurz skizzieren.",
  },
};

export function normalizePurchaseIntent(raw?: string | null): PurchaseIntent {
  if (raw === "upgrade" || raw === "pro" || raw === "professional" || raw === "express" || raw === "vnb-pilot") {
    return raw;
  }
  return "general";
}

export function getPurchaseIntentProfile(raw?: string | null): PurchaseIntentProfile {
  return INTENT_PROFILES[normalizePurchaseIntent(raw)];
}

export function listPurchaseIntentProfiles() {
  return [
    INTENT_PROFILES.upgrade,
    INTENT_PROFILES.pro,
    INTENT_PROFILES.professional,
    INTENT_PROFILES.express,
    INTENT_PROFILES["vnb-pilot"],
    INTENT_PROFILES.general,
  ];
}
