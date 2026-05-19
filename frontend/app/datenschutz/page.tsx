import type { Metadata } from "next";
import { LegalPageShell, LegalSection, PlaceholderNotice } from "@/components/layout/LegalPageShell";
import { legalCompany } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Datenschutz | GridCheck",
  description: "Datenschutzhinweise der GridCheck Plattform",
};

export default function DatenschutzPage() {
  return (
    <LegalPageShell
      badge="Rechtliches"
      title="Datenschutzerklaerung"
      intro="Grundgeruest gemaess DSGVO fuer den Betrieb der GridCheck SaaS-Plattform. Vor Live-Betrieb mit echten Verarbeitungsverzeichnissen und AV-Vertraegen abstimmen."
    >
      <PlaceholderNotice />

      <LegalSection title="Verantwortlicher">
        <p>
          {legalCompany.name}
          <br />
          {legalCompany.street}
          <br />
          {legalCompany.city}
          <br />
          E-Mail:{" "}
          <a href={`mailto:${legalCompany.privacyEmail}`} className="text-brand-cyan hover:underline">
            {legalCompany.privacyEmail}
          </a>
        </p>
      </LegalSection>

      <LegalSection title="Verarbeitungszwecke">
        <ul className="list-disc space-y-2 pl-5">
          <li>Bereitstellung des Kontos und der Plattformfunktionen (Authentifizierung, Projekte, Analysen)</li>
          <li>Erstellung revisionssicherer Protokolle und Audit-Exporte</li>
          <li>Abwicklung von Bestellungen, Lizenzen und Support-Anfragen</li>
          <li>Betrieb, Sicherheit, Fehleranalyse und Missbrauchspraevention</li>
          <li>Erfuellung gesetzlicher Aufbewahrungs- und Nachweispflichten</li>
        </ul>
      </LegalSection>

      <LegalSection title="Rechtsgrundlagen (Auswahl)">
        <ul className="list-disc space-y-2 pl-5">
          <li>Art. 6 Abs. 1 lit. b DSGVO – Vertragserfuellung und vorvertragliche Massnahmen</li>
          <li>Art. 6 Abs. 1 lit. f DSGVO – berechtigtes Interesse an sicherem Betrieb und Produktverbesserung</li>
          <li>Art. 6 Abs. 1 lit. c DSGVO – rechtliche Verpflichtungen, soweit einschlaegig</li>
          <li>Art. 6 Abs. 1 lit. a DSGVO – Einwilligung, soweit fuer optionale Cookies oder Newsletter erforderlich</li>
        </ul>
      </LegalSection>

      <LegalSection title="Kategorien verarbeiteter Daten">
        <ul className="list-disc space-y-2 pl-5">
          <li>Stammdaten (Name, E-Mail, Organisation, Rolle)</li>
          <li>Projekt- und Standortangaben, technische Eingaben und Ergebnisdaten</li>
          <li>Nutzungs-, Protokoll- und Sicherheitsdaten (z. B. IP-Adresse, Zeitstempel, Geraetehinweise)</li>
          <li>Zahlungs- und Abrechnungsmetadaten bei kostenpflichtigen Paketen (ueber Zahlungsdienstleister)</li>
        </ul>
      </LegalSection>

      <LegalSection title="Cookies und lokale Speicherung">
        <p>
          Wir setzen technisch notwendige Cookies bzw. lokale Speicher ein, um Anmeldung, Sitzungen, Sicherheit und
          grundlegende UI-Praeferenzen zu ermoeglichen. Optionale Analyse- oder Marketing-Cookies werden – sofern
          eingesetzt – erst nach Einwilligung aktiviert.
        </p>
        <p>
          PWA-Funktionen koennen zusaetzliche lokale Speicherung (z. B. Offline-Hinweise) nutzen. Details zu einzelnen
          Technologien sind vor Go-Live im Cookie-/Consent-Banner zu dokumentieren.
        </p>
      </LegalSection>

      <LegalSection title="Empfaenger und Auftragsverarbeiter">
        <p>
          Daten koennen an Hosting-, Datenbank-, Zahlungs-, E-Mail- und Karten-Dienstleister uebermittelt werden, soweit
          dies fuer den Betrieb erforderlich ist. Mit Auftragsverarbeitern werden AV-Vertraege geschlossen; Verarbeitung
          ausserhalb der EU/EWR erfolgt nur mit geeigneten Garantien (z. B. Standardvertragsklauseln).
        </p>
        <p className="text-text-dim">[Liste der konkreten Dienstleister vor Live eintragen]</p>
      </LegalSection>

      <LegalSection title="Speicherdauer">
        <p>
          Personenbezogene Daten werden nur so lange gespeichert, wie es fuer die genannten Zwecke erforderlich ist oder
          gesetzliche Aufbewahrungsfristen bestehen. Revisionssichere Berechnungs- und Auditdaten koennen laenger
          gespeichert werden, soweit dies fuer Nachvollziehbarkeit und Compliance erforderlich ist.
        </p>
      </LegalSection>

      <LegalSection title="Ihre Rechte">
        <p>
          Sie haben Rechte auf Auskunft, Berichtigung, Loeschung, Einschraenkung, Datenuebertragbarkeit, Widerspruch
          sowie Widerruf erteilter Einwilligungen. Beschwerden koennen bei einer Datenschutz-Aufsichtsbehoerde eingereicht
          werden.
        </p>
      </LegalSection>

      <LegalSection title="Kontakt Datenschutz">
        <p>
          Anfragen richten Sie bitte an:{" "}
          <a href={`mailto:${legalCompany.privacyEmail}`} className="text-brand-cyan hover:underline">
            {legalCompany.privacyEmail}
          </a>
        </p>
      </LegalSection>
    </LegalPageShell>
  );
}
