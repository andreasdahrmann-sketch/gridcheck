import { registerHrefForPlan } from "@/lib/billing-plans";

export type PublicPricingTier = {
  id: string;
  name: string;
  price: string;
  priceNote?: string;
  category: string;
  description: string;
  highlights: string[];
  featured?: boolean;
  cta: { label: string; href: string };
};

export const PUBLIC_PRICING_TIERS: PublicPricingTier[] = [
  {
    id: "free",
    name: "Free Check",
    price: "0 EUR",
    priceNote: "3 Checks pro Nutzerkonto",
    category: "Einstieg",
    description: "Erstes Screening mit kompakter Basisindikation vor kostenpflichtigem Paket.",
    highlights: [
      "Schneller Machbarkeits- und Risikoindikator",
      "Ideal fuer erste Standort- oder Opportunity-Pruefung",
      "Upgrade bei Bedarf auf Basic oder Premium",
    ],
    cta: { label: "Check starten", href: "/projektierer" },
  },
  {
    id: "basic",
    name: "Basic Schnellcheck",
    price: "249 EUR",
    category: "Self-Serve Einzelprojekt",
    description: "Fruehe Netzanschluss-Klarheit vor Antrag und Detailplanung mit kompaktem Basis-Scope.",
    highlights: [
      "Basis-Report fuer einzelnes Vorhaben",
      "Pay-per-Use ohne laufende Lizenz",
      "Hybrid-, Speicher- und Trassenlogik bewusst begrenzt",
    ],
    cta: { label: "Basic buchen", href: registerHrefForPlan("basic") },
  },
  {
    id: "premium",
    name: "Premium Pre-Check",
    price: "749 EUR",
    category: "Self-Serve Vertiefung",
    description: "Fuer Projekte, bei denen Bedingungen, Engpaesse und Darstellbarkeit frueh belastbar werden muessen.",
    highlights: [
      "Premium-Scope mit Hybrid- und Speicherperspektive",
      "Trassen- und Stakeholder-Argumentation sichtbar",
      "Self-Serve ohne operativen Follow-up",
    ],
    featured: true,
    cta: { label: "Premium buchen", href: registerHrefForPlan("premium") },
  },
  {
    id: "professional",
    name: "Professional Anschlussstrategie",
    price: "1.490 EUR",
    category: "Servicepfad",
    description: "Strategische Anschlussdarstellung mit sichtbarem operativem Follow-up vor Kapitalbindung oder IC-Freigabe.",
    highlights: [
      "Professional-Reportscope",
      "Operativer Nachlauf statt stiller Self-Serve-Abschluss",
      "Kein Express-SLA und kein VNB-Pilot inklusive",
    ],
    cta: { label: "Professional buchen", href: registerHrefForPlan("professional") },
  },
  {
    id: "pro",
    name: "Pro Lizenz",
    price: "ab 1.290 EUR / Monat",
    category: "SaaS",
    description: "Laufende Nutzung fuer Teams mit wiederkehrender Projektpipeline und Premium-Tiefe im Self-Serve.",
    highlights: [
      "Inklusiv-Analysen pro Abrechnungsperiode",
      "Fortlaufende Vorqualifizierung im Team",
      "Professional und Express bleiben separate Pfade",
    ],
    featured: true,
    cta: { label: "Pro Lizenz buchen", href: registerHrefForPlan("pro") },
  },
  {
    id: "vnb_pilot",
    name: "VNB Pilot",
    price: "auf Anfrage",
    category: "Pilot",
    description: "Netzbetreiber-nahe Pilotierung, Prozessintegration und abgestimmte Rollout-Szenarien.",
    highlights: [
      "Kein Self-Serve-Checkout",
      "Abgestimmter Pilot- und Servicepfad",
      "Fuer operative Prozess- und Rollout-Fragen",
    ],
    cta: { label: "Pilot anfragen", href: "/contact?intent=vnb" },
  },
];

export const EXPRESS_ADDON = {
  name: "Express",
  price: "Add-on",
  description:
    "Zeitkritischer Bearbeitungs- und Abstimmungspfad. Veraendert den technischen Analyseumfang nicht automatisch – das zugrunde liegende Paket bleibt massgeblich.",
};

export const PRICING_COMPARISON_ROWS = [
  { label: "Zielgruppe", free: "Erstscreening", basic: "Einzelvorhaben", premium: "Komplexe Einzelfaelle", pro: "Projektpipeline", professional: "Kritische Einzelfaelle", pilot: "Netzbetreiber" },
  { label: "Scope", free: "Basis", basic: "Basis-Report", premium: "Premium-Report", pro: "Premium inkl.", professional: "Professional + Follow-up", pilot: "Abgestimmt" },
  { label: "Checkout", free: "In App", basic: "Stripe", premium: "Stripe", pro: "Stripe Abo", professional: "Stripe", pilot: "Kontakt" },
] as const;
