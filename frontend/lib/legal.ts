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
 *
 * Sonderfall AUFSICHTSBEHOERDE:
 *   - Falls AUFSICHTSBEHOERDE noch das Token-Default ist (nicht explizit gesetzt)
 *     UND HOST_BUNDESLAND auf ein bekanntes Bundesland zeigt,
 *     wird die Aufsichtsbehoerde automatisch aus AUFSICHTSBEHOERDEN_BY_BUNDESLAND
 *     aufgeloest. Ein explizit gesetzter AUFSICHTSBEHOERDE-Wert (z. B. ueber ENV)
 *     hat Vorrang und ueberschreibt die automatische Aufloesung.
 */
export function renderLegalText(template: string): string {
  return template.replace(/\{\{([A-Z_]+)\}\}/g, (match, key: string) => {
    if (key === "AUFSICHTSBEHOERDE") {
      return resolveAufsichtsbehoerdeForLegalData();
    }
    const value = LEGAL_DATA[key as LegalDataKey];
    return value ?? match;
  });
}

/** Liefert true, wenn der Wert noch das Token-Default ist (also nicht ausgefuellt). */
export function isLegalTokenUnset(key: LegalDataKey): boolean {
  return LEGAL_DATA[key] === `{{${key}}}`;
}

// ---------------------------------------------------------------------------
// Aufsichtsbehoerden-Mapping (Datenschutz-Aufsicht je Bundesland)
// ---------------------------------------------------------------------------
//
// Stand: Recherche 2026 anhand offizieller DSB-Webseiten (BlnBDI, BayLDA,
// LfDI BW, LDI NRW, HBDI, LfD Niedersachsen, SDB, LfD ST, TLfDI, LDA BB,
// LfDI MV, ULD, HmbBfDI, LfDI HB, UDS Saarland, LfDI RLP).
//
// HINWEIS: Diese Daten dienen ausschliesslich als technischer Default fuer
// die Datenschutzerklaerung. Aktualitaet (Anschriften, Kontaktdaten, Wechsel
// der Behoerdenleitung) ist NICHT garantiert. Vor Live-Schaltung muss der
// User die zustaendige Behoerde bestaetigen oder per ENV/LEGAL_DATA ueber-
// schreiben (Override siehe renderLegalText-Doc).
//
// Telefonnummern bewusst optional — im Zweifel weggelassen statt erfunden.
// E-Mails bewusst weggelassen, da Adressformate sich aendern; bei Bedarf
// per Override-Pfad ergaenzen.

export type AufsichtsbehoerdeRecord = {
  /** Anzeigename der Behoerde (Lang- oder Kurzform). */
  name: string;
  /** Strasse + Hausnummer. */
  anschrift: string;
  /** PLZ + Ort. */
  ort: string;
  /** Optionale Webseite. */
  webseite?: string;
  /** Optionales Telefon. */
  telefon?: string;
  /** Optionale Kontakt-E-Mail. */
  email?: string;
};

export const AUFSICHTSBEHOERDEN_BY_BUNDESLAND: Record<string, AufsichtsbehoerdeRecord> = {
  "baden-wuerttemberg": {
    name: "Der Landesbeauftragte fuer den Datenschutz und die Informationsfreiheit Baden-Wuerttemberg (LfDI BW)",
    anschrift: "Lautenschlagerstrasse 20",
    ort: "70173 Stuttgart",
    webseite: "https://www.baden-wuerttemberg.datenschutz.de/",
  },
  bayern: {
    name: "Bayerisches Landesamt fuer Datenschutzaufsicht (BayLDA)",
    anschrift: "Promenade 18",
    ort: "91522 Ansbach",
    webseite: "https://www.lda.bayern.de/",
  },
  berlin: {
    name: "Berliner Beauftragte fuer Datenschutz und Informationsfreiheit (BlnBDI)",
    anschrift: "Friedrichstrasse 219",
    ort: "10969 Berlin",
    webseite: "https://www.datenschutz-berlin.de/",
  },
  brandenburg: {
    name: "Die Landesbeauftragte fuer den Datenschutz und fuer das Recht auf Akteneinsicht Brandenburg (LDA BB)",
    anschrift: "Stahnsdorfer Damm 77",
    ort: "14532 Kleinmachnow",
    webseite: "https://www.lda.brandenburg.de/",
  },
  bremen: {
    name: "Die Landesbeauftragte fuer Datenschutz und Informationsfreiheit der Freien Hansestadt Bremen (LfDI HB)",
    anschrift: "Arndtstrasse 1",
    ort: "27570 Bremerhaven",
    webseite: "https://www.datenschutz.bremen.de/",
  },
  hamburg: {
    name: "Der Hamburgische Beauftragte fuer Datenschutz und Informationsfreiheit (HmbBfDI)",
    anschrift: "Ludwig-Erhard-Strasse 22",
    ort: "20459 Hamburg",
    webseite: "https://datenschutz-hamburg.de/",
  },
  hessen: {
    name: "Der Hessische Beauftragte fuer Datenschutz und Informationsfreiheit (HBDI)",
    anschrift: "Gustav-Stresemann-Ring 1",
    ort: "65189 Wiesbaden",
    webseite: "https://datenschutz.hessen.de/",
  },
  "mecklenburg-vorpommern": {
    name: "Der Landesbeauftragte fuer Datenschutz und Informationsfreiheit Mecklenburg-Vorpommern (LfDI MV)",
    anschrift: "Lennestrasse 1",
    ort: "19053 Schwerin",
    webseite: "https://www.datenschutz-mv.de/",
  },
  niedersachsen: {
    name: "Die Landesbeauftragte fuer den Datenschutz Niedersachsen (LfD Niedersachsen)",
    anschrift: "Prinzenstrasse 5",
    ort: "30159 Hannover",
    webseite: "https://lfd.niedersachsen.de/",
  },
  "nordrhein-westfalen": {
    name: "Landesbeauftragte fuer Datenschutz und Informationsfreiheit Nordrhein-Westfalen (LDI NRW)",
    anschrift: "Kavalleriestrasse 2-4",
    ort: "40213 Duesseldorf",
    webseite: "https://www.ldi.nrw.de/",
  },
  "rheinland-pfalz": {
    name: "Der Landesbeauftragte fuer den Datenschutz und die Informationsfreiheit Rheinland-Pfalz (LfDI RLP)",
    anschrift: "Hintere Bleiche 34",
    ort: "55116 Mainz",
    webseite: "https://www.datenschutz.rlp.de/",
  },
  saarland: {
    name: "Unabhaengiges Datenschutzzentrum Saarland (UDS Saarland)",
    anschrift: "Fritz-Dobisch-Strasse 12",
    ort: "66111 Saarbruecken",
    webseite: "https://www.datenschutz.saarland.de/",
  },
  sachsen: {
    name: "Die Saechsische Datenschutz- und Transparenzbeauftragte (SDB)",
    anschrift: "Devrientstrasse 1",
    ort: "01067 Dresden",
    webseite: "https://www.saechsdsb.de/",
  },
  "sachsen-anhalt": {
    name: "Landesbeauftragter fuer den Datenschutz Sachsen-Anhalt (LfD ST)",
    anschrift: "Leiterstrasse 9",
    ort: "39104 Magdeburg",
    webseite: "https://datenschutz.sachsen-anhalt.de/",
  },
  "schleswig-holstein": {
    name: "Unabhaengiges Landeszentrum fuer Datenschutz Schleswig-Holstein (ULD)",
    anschrift: "Holstenstrasse 98",
    ort: "24103 Kiel",
    webseite: "https://www.datenschutzzentrum.de/",
  },
  thueringen: {
    name: "Thueringer Landesbeauftragter fuer den Datenschutz und die Informationsfreiheit (TLfDI)",
    anschrift: "Haesslerstrasse 8",
    ort: "99096 Erfurt",
    webseite: "https://www.tlfdi.de/",
  },
};

/**
 * Normalisiert einen Bundesland-String fuer Lookup-Zwecke:
 *  - trim
 *  - lowercase
 *  - Umlaute -> ae/oe/ue/ss
 *  - Whitespace und " / "/"_" -> "-"
 *  - haeufige Synonyme (NRW, BW, M-V, S-H, RLP) auf kanonische Keys
 */
function normalizeBundeslandKey(input: string): string {
  if (!input) return "";
  const lowered = input
    .trim()
    .toLowerCase()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .replace(/ß/g, "ss")
    .replace(/[\s_/]+/g, "-");
  const synonyms: Record<string, string> = {
    bw: "baden-wuerttemberg",
    by: "bayern",
    be: "berlin",
    bb: "brandenburg",
    hb: "bremen",
    hh: "hamburg",
    he: "hessen",
    mv: "mecklenburg-vorpommern",
    "m-v": "mecklenburg-vorpommern",
    ni: "niedersachsen",
    nrw: "nordrhein-westfalen",
    "nordrhein-westf.": "nordrhein-westfalen",
    rlp: "rheinland-pfalz",
    sl: "saarland",
    sn: "sachsen",
    st: "sachsen-anhalt",
    sh: "schleswig-holstein",
    "s-h": "schleswig-holstein",
    th: "thueringen",
  };
  if (synonyms[lowered]) return synonyms[lowered];
  return lowered;
}

/**
 * Liefert die Aufsichtsbehoerde formatiert als "Name, Anschrift, Ort".
 * Robust gegen Gross-/Kleinschreibung, Umlaute und uebliche Abkuerzungen.
 *
 * Bei unbekanntem Bundesland wird ein leerer String zurueckgegeben — die
 * aufrufende Stelle (renderLegalText) entscheidet, wie sie damit umgeht
 * (Fallback auf das Token-Literal, damit fehlende Daten sichtbar bleiben).
 */
export function resolveAufsichtsbehoerde(bundesland: string): string {
  const key = normalizeBundeslandKey(bundesland);
  const rec = AUFSICHTSBEHOERDEN_BY_BUNDESLAND[key];
  if (!rec) return "";
  return `${rec.name}, ${rec.anschrift}, ${rec.ort}`;
}

/**
 * Interne Hilfe fuer renderLegalText:
 *  - explizit gesetzter AUFSICHTSBEHOERDE-Wert (nicht das Token-Literal) wird
 *    unveraendert zurueckgegeben (Override-Moeglichkeit)
 *  - sonst: Aufloesung ueber HOST_BUNDESLAND
 *  - falls weder Override noch bekanntes Bundesland: Token-Literal beibehalten
 */
function resolveAufsichtsbehoerdeForLegalData(): string {
  const explicit = LEGAL_DATA.AUFSICHTSBEHOERDE;
  if (explicit && explicit !== "{{AUFSICHTSBEHOERDE}}") {
    return explicit;
  }
  const bundesland = LEGAL_DATA.HOST_BUNDESLAND;
  if (!bundesland || bundesland === "{{HOST_BUNDESLAND}}") {
    return "{{AUFSICHTSBEHOERDE}}";
  }
  const resolved = resolveAufsichtsbehoerde(bundesland);
  if (!resolved) {
    return "{{AUFSICHTSBEHOERDE}}";
  }
  return resolved;
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
