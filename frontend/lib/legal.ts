/**
 * Zentrale Rechts-/Compliance-Daten fuer Impressum, Datenschutz, AGB und Cookie-Notice.
 *
 * Hinweis: Alle firmenspezifischen Werte sind als Token hinterlegt
 * ({{FIRMA_NAME}}, {{HRB_NR}}, ...). Der Token bleibt im Live-Build sichtbar,
 * solange er nicht durch echte Werte ersetzt wurde — das ist Absicht, damit die
 * Seiten nie versehentlich mit erfundenen Firmendaten online gehen.
 *
 * Ersetzung erfolgt entweder
 *   (a) per ENV (NEXT_PUBLIC_LEGAL_*) zur Build-Zeit, oder
 *   (b) per Find&Replace direkt in dieser Datei (PowerShell-Snippet siehe Bericht).
 */

export type LegalDataKey =
  | "FIRMA_NAME"
  | "RECHTSFORM"
  | "STRASSE_HAUSNR"
  | "PLZ_ORT"
  | "LAND"
  | "USTID"
  | "REGISTERGERICHT"
  | "HRB_NR"
  | "GESCHAEFTSFUEHRER"
  | "TELEFON"
  | "KONTAKT_EMAIL"
  | "DPO_NAME"
  | "DPO_EMAIL"
  | "HOST_BUNDESLAND"
  | "AUFSICHTSBEHOERDE"
  | "GERICHTSSTAND_ORT"
  | "STAND_DATUM";

/**
 * Default = der Token selbst. So bleibt sofort sichtbar, dass eine Pflichtangabe
 * fehlt, und es entstehen keine erfundenen Firmendaten im UI.
 */
export const LEGAL_DATA: Record<LegalDataKey, string> = {
  FIRMA_NAME: process.env.NEXT_PUBLIC_LEGAL_COMPANY_NAME ?? "{{FIRMA_NAME}}",
  RECHTSFORM: process.env.NEXT_PUBLIC_LEGAL_COMPANY_FORM ?? "{{RECHTSFORM}}",
  STRASSE_HAUSNR: process.env.NEXT_PUBLIC_LEGAL_STREET ?? "{{STRASSE_HAUSNR}}",
  PLZ_ORT: process.env.NEXT_PUBLIC_LEGAL_CITY ?? "{{PLZ_ORT}}",
  LAND: process.env.NEXT_PUBLIC_LEGAL_COUNTRY ?? "{{LAND}}",
  USTID: process.env.NEXT_PUBLIC_LEGAL_USTID ?? "{{USTID}}",
  REGISTERGERICHT: process.env.NEXT_PUBLIC_LEGAL_REGISTERGERICHT ?? "{{REGISTERGERICHT}}",
  HRB_NR: process.env.NEXT_PUBLIC_LEGAL_HRB_NR ?? "{{HRB_NR}}",
  GESCHAEFTSFUEHRER: process.env.NEXT_PUBLIC_LEGAL_GESCHAEFTSFUEHRER ?? "{{GESCHAEFTSFUEHRER}}",
  TELEFON: process.env.NEXT_PUBLIC_LEGAL_TELEFON ?? "{{TELEFON}}",
  KONTAKT_EMAIL: process.env.NEXT_PUBLIC_LEGAL_CONTACT_EMAIL ?? "{{KONTAKT_EMAIL}}",
  DPO_NAME: process.env.NEXT_PUBLIC_LEGAL_DPO_NAME ?? "{{DPO_NAME}}",
  DPO_EMAIL: process.env.NEXT_PUBLIC_LEGAL_DPO_EMAIL ?? "{{DPO_EMAIL}}",
  HOST_BUNDESLAND: process.env.NEXT_PUBLIC_LEGAL_HOST_BUNDESLAND ?? "{{HOST_BUNDESLAND}}",
  AUFSICHTSBEHOERDE: process.env.NEXT_PUBLIC_LEGAL_AUFSICHTSBEHOERDE ?? "{{AUFSICHTSBEHOERDE}}",
  GERICHTSSTAND_ORT: process.env.NEXT_PUBLIC_LEGAL_GERICHTSSTAND_ORT ?? "{{GERICHTSSTAND_ORT}}",
  STAND_DATUM: process.env.NEXT_PUBLIC_LEGAL_STAND_DATUM ?? "{{STAND_DATUM}}",
};

/**
 * Ersetzt {{TOKEN}}-Platzhalter in Templates.
 * Tokens, fuer die kein Wert in LEGAL_DATA gesetzt wurde, bleiben unveraendert
 * stehen — bewusst, damit fehlende Pflichtangaben sichtbar sind.
 */
export function renderLegalText(template: string): string {
  return template.replace(/\{\{([A-Z_]+)\}\}/g, (match, key: string) => {
    const value = LEGAL_DATA[key as LegalDataKey];
    return value ?? match;
  });
}

/** Liefert true, wenn der Wert noch das Token-Default ist (also nicht ausgefuellt). */
export function isLegalTokenUnset(key: LegalDataKey): boolean {
  return LEGAL_DATA[key] === `{{${key}}}`;
}

// ---------------------------------------------------------------------------
// Auftragsverarbeiter / Empfaenger nach DSGVO Art. 28 / Art. 13
// ---------------------------------------------------------------------------

export type DataProcessorClass = "A" | "B" | "C" | "D" | "E";

export type DataTransferBasis =
  | "EU_EWR"
  | "SCC" // EU-Standardvertragsklauseln
  | "SCC_DPF" // SCC + EU-US Data Privacy Framework
  | "ADEQUACY"; // Angemessenheitsbeschluss

export type DataProcessor = {
  /** Anzeigename */
  name: string;
  /** Zweck der Verarbeitung */
  purpose: string;
  /** Sitz / Verarbeitungsort */
  location: string;
  /** Rechtsgrundlage Datenuebermittlung */
  transferBasis: DataTransferBasis;
  /** Art. 6 DSGVO Rechtsgrundlage */
  legalBasis: string;
  /** AVV/DPA abgeschlossen? */
  dpaSigned: boolean;
  /** Im aktuellen Build aktiv eingebunden? */
  active: boolean;
  /** Verarbeitete Datenkategorien (Kurzform) */
  dataCategories: string[];
  /** Optional: Link zu DPA / Privacy Policy des Anbieters */
  vendorPrivacyUrl?: string;
};

/**
 * Liste der Auftragsverarbeiter / Empfaenger.
 *
 * Stand: nur Anbieter, die aus Repo-Stand (DECISIONS.md, COMPLIANCE_AUDIT.md,
 * Deployment-Regeln) belegbar sind. Stripe und Sentry sind als `active: false`
 * vorbereitet — der User schaltet sie ein, sobald sie produktiv aktiviert sind
 * und ein AVV vorliegt.
 *
 * WICHTIG: Diese Liste darf NICHT mit erfundenen Anbietern erweitert werden.
 * Jeder Eintrag braucht einen real abgeschlossenen AVV oder vergleichbaren
 * Vertrag.
 */
export const DATA_PROCESSORS: DataProcessor[] = [
  {
    name: "Railway (Railway Corp.)",
    purpose: "Hosting Backend-API + verwaltete PostgreSQL/PostGIS-Instanz",
    location: "EU-Region (Frankfurt/Amsterdam, je nach Projekt-Konfiguration)",
    transferBasis: "EU_EWR",
    legalBasis: "Art. 6 Abs. 1 lit. b DSGVO (Vertragserfuellung) i.V.m. Art. 28 DSGVO",
    dpaSigned: true,
    active: true,
    dataCategories: ["Stammdaten", "Projektdaten", "Audit-Logs", "Zahlungsmetadaten"],
    vendorPrivacyUrl: "https://railway.com/legal/privacy",
  },
  {
    name: "Vercel Inc.",
    purpose: "Hosting Frontend (Next.js), Edge-CDN, Build-Pipeline",
    location: "USA (Edge-Nodes weltweit, EU-Edges bevorzugt)",
    transferBasis: "SCC_DPF",
    legalBasis: "Art. 6 Abs. 1 lit. b DSGVO i.V.m. Art. 28 DSGVO; Art. 46 DSGVO (SCC) + EU-US Data Privacy Framework",
    dpaSigned: true,
    active: true,
    dataCategories: ["Verbindungsdaten (IP, User-Agent)", "Anfrage-Logs"],
    vendorPrivacyUrl: "https://vercel.com/legal/privacy-policy",
  },
  {
    name: "OpenStreetMap Foundation / Nominatim",
    purpose: "Geocoding (Adresse zu Koordinaten) und Reverse-Geocoding fuer Standorteingaben",
    location: "EU/UK (gemeinnuetzige Stiftung)",
    transferBasis: "EU_EWR",
    legalBasis: "Art. 6 Abs. 1 lit. b DSGVO (Vertragserfuellung) bzw. Art. 6 Abs. 1 lit. f DSGVO",
    dpaSigned: false,
    active: true,
    dataCategories: ["Standortabfragen (Adresse/Koordinaten)", "Verbindungsdaten"],
    vendorPrivacyUrl: "https://wiki.osmfoundation.org/wiki/Privacy_Policy",
  },
  {
    name: "Stripe Payments Europe, Ltd. / Stripe, Inc.",
    purpose: "Zahlungsabwicklung (Checkout, Abonnements, Rechnungsverwaltung)",
    location: "Irland (EU) und USA",
    transferBasis: "SCC_DPF",
    legalBasis: "Art. 6 Abs. 1 lit. b DSGVO (Vertragserfuellung); Art. 46 DSGVO (SCC) + EU-US Data Privacy Framework",
    dpaSigned: true,
    active: false,
    dataCategories: ["Zahlungsdaten", "Rechnungs-Stammdaten", "Transaktionsmetadaten"],
    vendorPrivacyUrl: "https://stripe.com/de/privacy",
  },
  {
    name: "Sentry (Functional Software, Inc.)",
    purpose: "Fehler- und Performance-Monitoring (Error-Tracking, Stacktraces)",
    location: "USA (EU-Region optional)",
    transferBasis: "SCC_DPF",
    legalBasis: "Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse: Stabilitaet/Sicherheit) bzw. Einwilligung",
    dpaSigned: true,
    active: false,
    dataCategories: ["Fehler-Stacktraces", "Browser-/Geraete-Hinweise", "User-Hashes"],
    vendorPrivacyUrl: "https://sentry.io/privacy/",
  },
];

export function activeDataProcessors(): DataProcessor[] {
  return DATA_PROCESSORS.filter((p) => p.active);
}

// ---------------------------------------------------------------------------
// Backwards-Compat: legalCompany — nicht mehr direkt verwenden.
// Bestehende Stellen wurden migriert, dieser Export bleibt nur, falls in
// anderem WIP noch Stellen darauf zugreifen, damit der Build nicht bricht.
// ---------------------------------------------------------------------------
export const legalCompany = {
  name: LEGAL_DATA.FIRMA_NAME,
  legalForm: LEGAL_DATA.RECHTSFORM,
  street: LEGAL_DATA.STRASSE_HAUSNR,
  city: `${LEGAL_DATA.PLZ_ORT}, ${LEGAL_DATA.LAND}`,
  contactEmail: LEGAL_DATA.KONTAKT_EMAIL,
  privacyEmail: LEGAL_DATA.DPO_EMAIL,
} as const;
