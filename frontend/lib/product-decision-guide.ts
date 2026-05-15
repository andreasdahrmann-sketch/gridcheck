export type DecisionGuideCard = {
  id: string;
  title: string;
  badge: string;
  whenToChoose: string;
  included: string;
  notFor: string;
  href: string;
  cta: string;
};

export type ProductFaqItem = {
  question: string;
  answer: string;
};

export const DECISION_GUIDE_CARDS: DecisionGuideCard[] = [
  {
    id: "basic",
    title: "Free / Basic",
    badge: "Basis-Scope",
    whenToChoose: "Wenn Sie einen Standort oder ein Vorhaben erstmals plausibilisieren wollen.",
    included: "Kompakter Basis-Run fuer fruehe Netzanschluss-Klarheit ohne tiefere Hybrid-, Speicher- oder Trassenlogik.",
    notFor: "Nicht geeignet fuer strategische Anschlussdarstellung oder vertiefte Stakeholder-/Umweltargumentation.",
    href: "/settings",
    cta: "Basispfad ansehen",
  },
  {
    id: "premium",
    title: "Premium Pre-Check",
    badge: "Self-Serve Vertiefung",
    whenToChoose: "Wenn Hybrid, Speicher, Trasse und Investoren-/Freigabereife frueh sauber bewertet werden muessen.",
    included: "Vertiefter Self-Serve-Report mit Premium-Scope fuer komplexere Einzelvorhaben.",
    notFor: "Nicht der richtige Pfad, wenn sichtbarer operativer Follow-up oder manuelle Anschlussstrategie noetig ist.",
    href: "/settings",
    cta: "Premium vergleichen",
  },
  {
    id: "pro",
    title: "Pro Lizenz",
    badge: "SaaS",
    whenToChoose: "Wenn mehrere Projekte fortlaufend im Team vorqualifiziert werden sollen.",
    included: "Laufende Premium-Tiefe im Self-Serve-Pfad mit wiederkehrender Nutzung ueber die Pipeline.",
    notFor: "Kein Ersatz fuer den betreuten Professional-Servicepfad bei kritischen Einzelfaellen.",
    href: "/contact?intent=pro",
    cta: "Pro abstimmen",
  },
  {
    id: "professional",
    title: "Professional Anschlussstrategie",
    badge: "Servicepfad",
    whenToChoose: "Wenn ein Einzelfall vor Antrag, EPC-Start oder IC-/Board-Freigabe strategisch verdichtet werden muss.",
    included: "Professional-Reportscope plus sichtbarer operativer Follow-up fuer Anschlussstrategie und Visualisierung.",
    notFor: "Nicht als allgemeiner Teamtarif gedacht und kein stilles Upgrade eines normalen Self-Serve-Runs.",
    href: "/contact?intent=professional",
    cta: "Professional anfragen",
  },
  {
    id: "pilot",
    title: "Express / VNB Pilot",
    badge: "Spezialpfad",
    whenToChoose: "Wenn entweder Zeitdruck dominiert oder ein abgestimmter Netzbetreiber-/Pilotkontext vorliegt.",
    included: "Express als Zeit-Zusatzpfad, VNB Pilot als abgestimmter Kontakt- und Rolloutpfad.",
    notFor: "Beides ersetzt kein passendes Analysepaket und erweitert den technischen Scope nicht automatisch.",
    href: "/contact?intent=express",
    cta: "Spezialpfad anfragen",
  },
];

export const PRODUCT_FAQS: ProductFaqItem[] = [
  {
    question: "Wann reicht Basic und wann brauche ich Premium?",
    answer:
      "Basic reicht fuer die erste Klarheit. Sobald Hybrid, Speicher, Trasse, Stakeholder-Abwaegung oder ein belastbarerer Einzelreport wichtig werden, ist Premium der saubere Self-Serve-Pfad.",
  },
  {
    question: "Was ist der Unterschied zwischen Pro und Professional?",
    answer:
      "Pro ist die laufende SaaS-Nutzung fuer mehrere Projekte. Professional ist der betreute Servicepfad fuer kritische Einzelvorhaben mit sichtbarem operativem Follow-up.",
  },
  {
    question: "Ist Express einfach ein hoeheres Paket?",
    answer:
      "Nein. Express ist ein Zeit- und Bearbeitungspfad. Der technische Analyseumfang kommt weiterhin aus dem zugrunde liegenden Paket und wird nicht still erweitert.",
  },
  {
    question: "Warum ist VNB Pilot kein normaler Checkout?",
    answer:
      "Weil VNB-nahe Pilotierung, Prozessintegration und Rollout typischerweise abgestimmt werden muessen. Deshalb bleibt der Pfad bewusst kontakt- und projektbasiert.",
  },
  {
    question: "Was passiert nach einem gekauften Run?",
    answer:
      "Der Run bleibt in History und Projektkontext sichtbar. Bei Professional oder Express wird zusaetzlich ein operativer Nachlauf statt eines stillen Self-Serve-Endpunkts markiert.",
  },
];

type NextStepGuidance = {
  title: string;
  summary: string;
  actions: Array<{ label: string; href: string }>;
};

export function getNextStepGuidance(offerId?: string | null, packageScope?: string | null): NextStepGuidance {
  if (offerId === "professional_anschlussstrategie" || packageScope === "professional") {
    return {
      title: "Sie befinden sich bereits im betreuten Servicepfad.",
      summary:
        "Der naechste sinnvolle Schritt ist nicht noch ein weiteres Self-Serve-Upgrade, sondern der operative Follow-up. Express lohnt sich nur bei zusaetzlichem Zeitdruck.",
      actions: [
        { label: "Professional anfragen", href: "/contact?intent=professional" },
        { label: "Express anfragen", href: "/contact?intent=express" },
      ],
    };
  }
  if (offerId === "pro_lizenz") {
    return {
      title: "Pro ist Ihr laufender Pipeline-Pfad.",
      summary:
        "Bleiben Sie fuer wiederkehrende Projekte im Pro-Pfad. Professional ist nur dann sinnvoll, wenn ein einzelner Fall strategisch begleitet werden muss.",
      actions: [
        { label: "Pro abstimmen", href: "/contact?intent=pro" },
        { label: "Professional anfragen", href: "/contact?intent=professional" },
      ],
    };
  }
  if (offerId === "premium_pre_check" || packageScope === "premium") {
    return {
      title: "Premium deckt die vertiefte Self-Serve-Sicht ab.",
      summary:
        "Wenn mehrere Projekte folgen, ist Pro der logischere Schritt. Wenn sichtbarer Follow-up, Anschlussstrategie oder manuelle Abstimmung noetig sind, fuehrt der Weg zu Professional.",
      actions: [
        { label: "Pro vergleichen", href: "/contact?intent=pro" },
        { label: "Professional anfragen", href: "/contact?intent=professional" },
      ],
    };
  }
  return {
    title: "Nach Basis- oder Free-Runs wird die Paketwahl wichtig.",
    summary:
      "Bleibt es beim kompakten Screening, reicht der Basispfad. Sobald mehr Argumentation, Premium-Scope oder laufende Nutzung gebraucht werden, sollten Premium, Pro oder Professional sauber getrennt geprueft werden.",
    actions: [
      { label: "Tarife ansehen", href: "/settings" },
      { label: "Upgrade anfragen", href: "/contact?intent=upgrade" },
    ],
  };
}

export function getBillingEventLabel(eventType: string) {
  if (eventType === "checkout.session.created") return "Checkout gestartet";
  if (eventType === "checkout.session.status") return "Checkout Rueckkehr verarbeitet";
  if (eventType === "billing_portal.session.created") return "Billing Portal geoeffnet";
  if (eventType === "customer.subscription.created") return "Subscription gestartet";
  if (eventType === "customer.subscription.updated") return "Subscription aktualisiert";
  if (eventType === "customer.subscription.deleted") return "Subscription beendet";
  if (eventType === "invoice.paid") return "Zahlung bestaetigt";
  if (eventType === "invoice.payment_failed") return "Zahlung fehlgeschlagen";
  if (eventType === "ops.followup.claimed") return "Follow-up uebernommen";
  if (eventType === "ops.followup.status_changed") return "Follow-up Status geaendert";
  return eventType;
}

export function getEntitlementStatusLabel(status: string) {
  if (status === "active") return "aktiv";
  if (status === "consumed") return "verbraucht";
  if (status === "pending") return "Aktivierung offen";
  if (status === "ops_pending") return "wartet auf Service";
  if (status === "checkout_completed") return "Checkout bestaetigt";
  if (status === "canceled") return "beendet";
  if (status === "trialing") return "Testphase";
  if (status === "past_due") return "Zahlung offen";
  return status;
}

export function getServiceStatusLabel(status: string) {
  if (status === "pending_review") return "wartet auf Bearbeitung";
  if (status === "in_progress") return "in Bearbeitung";
  if (status === "completed") return "abgeschlossen";
  if (status === "not_required") return "kein Nachlauf";
  return status;
}

export function getRunStatusLabel(status: string) {
  if (status === "completed") return "abgeschlossen";
  if (status === "failed") return "fehlgeschlagen";
  if (status === "paywall_blocked") return "durch Paketgrenze blockiert";
  if (status === "validation_failed") return "an Eingaben gescheitert";
  return status;
}

export function getBillingEventStatusLabel(status: string) {
  if (status === "succeeded") return "erfolgreich";
  if (status === "completed") return "abgeschlossen";
  if (status === "pending") return "wartet auf Bestaetigung";
  if (status === "failed") return "fehlgeschlagen";
  if (status === "canceled") return "abgebrochen";
  return status;
}

export function getBillingEventSummary(eventType: string, status: string) {
  if (eventType === "checkout.session.created") {
    return "Ein Self-Serve-Checkout wurde gestartet, Paketrechte entstehen erst nach erfolgreicher Bestaetigung.";
  }
  if (eventType === "checkout.session.status") {
    return "Der Rueckweg aus dem Checkout wurde verarbeitet und der Tarifstatus aktualisiert.";
  }
  if (eventType === "invoice.paid") {
    return "Die zugehoerige Zahlung wurde bestaetigt und der laufende Nutzungsstatus bleibt aktiv.";
  }
  if (eventType === "invoice.payment_failed") {
    return "Eine Zahlung konnte nicht abgeschlossen werden. Betroffene Rechte sollten geprueft werden.";
  }
  if (eventType === "ops.followup.claimed" || eventType === "ops.followup.status_changed") {
    return "Ein betreuter Servicepfad wurde intern weiterbearbeitet und der operative Status aktualisiert.";
  }
  return `Status ${status}.`;
}
