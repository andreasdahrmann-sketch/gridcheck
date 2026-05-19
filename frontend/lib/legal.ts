/** Platzhalter fuer Impressum/Datenschutz/AGB — vor Live per ENV setzen. */
export const legalCompany = {
  name: process.env.NEXT_PUBLIC_LEGAL_COMPANY_NAME ?? "[Firmenname – Platzhalter]",
  legalForm: process.env.NEXT_PUBLIC_LEGAL_COMPANY_FORM ?? "[Rechtsform, z. B. GmbH]",
  street: process.env.NEXT_PUBLIC_LEGAL_STREET ?? "[Strasse und Hausnummer]",
  city: process.env.NEXT_PUBLIC_LEGAL_CITY ?? "[PLZ Ort], Deutschland",
  contactEmail: process.env.NEXT_PUBLIC_LEGAL_CONTACT_EMAIL ?? "kontakt@example.com",
  privacyEmail: process.env.NEXT_PUBLIC_LEGAL_PRIVACY_EMAIL ?? "datenschutz@example.com",
} as const;
