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
          Verantwortlich fuer die Datenverarbeitung im Sinne der DSGVO:
        </p>
        <p>
          <strong className="text-white">{legalCompany.name}</strong>
          <br />
          {legalCompany.legalForm}
          <br />
          {legalCompany.street}
          <br />
          {legalCompany.city}
        </p>
        <p>
          Datenschutzkontakt:{" "}
          <a href={`mailto:${legalCompany.privacyEmail}`} className="text-brand-cyan hover:underline">
            {legalCompany.privacyEmail}
          </a>
        </p>
        <p className="text-text-dim">[Datenschutzbeauftragter vor Live eintragen, falls erforderlich]</p>
      </LegalSection>

      <LegalSection title="Uebersicht der Verarbeitung">
        <p>
          GridCheck verarbeitet personenbezogene Daten, um Konten bereitzustellen, technische Netzanschluss-Analysen
          durchzufuehren, Abrechnungen abzuwickeln und den sicheren Betrieb der Plattform zu gewaehrleisten.
        </p>
      </LegalSection>

      <LegalSection title="Datenkategorien">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong className="text-white">Stammdaten:</strong> Name, E-Mail, Organisation, Rolle, Kontoeinstellungen
          </li>
          <li>
            <strong className="text-white">Projekt- und Fachdaten:</strong> Standortangaben, technische Eingaben,
            Ergebnisdaten, Annahmen, Audit-Protokolle
          </li>
          <li>
            <strong className="text-white">Nutzungs- und Protokolldaten:</strong> IP-Adresse, Zeitstempel, Session- und
            Sicherheitsereignisse, Geraete- und Browserhinweise
          </li>
          <li>
            <strong className="text-white">Abrechnungsdaten:</strong> Paketwahl, Zahlungsstatus, Rechnungsmetadaten
            (Zahlungsdaten beim Zahlungsdienstleister)
          </li>
          <li>
            <strong className="text-white">Kommunikationsdaten:</strong> Support-Anfragen, Passwort-Reset-Anfragen
          </li>
        </ul>
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

      <LegalSection title="Cookies und lokale Speicherung">
        <p>
          Wir setzen technisch notwendige Cookies bzw. lokale Speicher ein, um Anmeldung, Sitzungen, Sicherheit und
          grundlegende UI-Praeferenzen zu ermoeglichen. Optionale Analyse- oder Marketing-Cookies werden – sofern
          eingesetzt – erst nach Einwilligung aktiviert.
        </p>
        <p>
          PWA-Funktionen koennen zusaetzliche lokale Speicherung (z. B. Offline-Hinweise, Formular-Entwuerfe) nutzen.
          Details zu einzelnen Technologien sind vor Go-Live im Cookie-/Consent-Banner zu dokumentieren.
        </p>
      </LegalSection>

      <LegalSection title="Empfaenger und Auftragsverarbeiter">
        <p>
          Daten koennen an Hosting-, Datenbank-, Zahlungs-, E-Mail- und Karten-Dienstleister uebermittelt werden, soweit
          dies fuer den Betrieb erforderlich ist. Mit Auftragsverarbeitern werden AV-Vertraege geschlossen; Verarbeitung
          ausserhalb der EU/EWR erfolgt nur mit geeigneten Garantien (z. B. Standardvertragsklauseln).
        </p>
        <ul className="list-disc space-y-2 pl-5 text-text-dim">
          <li>Hosting / Infrastruktur: [z. B. Railway, Vercel – vor Live eintragen]</li>
          <li>Datenbank: [PostgreSQL-Anbieter – vor Live eintragen]</li>
          <li>Zahlungsabwicklung: [z. B. Stripe – vor Live eintragen]</li>
          <li>E-Mail-Versand: [SMTP-Anbieter – vor Live eintragen]</li>
        </ul>
      </LegalSection>

      <LegalSection title="Speicherdauer">
        <p>
          Personenbezogene Daten werden nur so lange gespeichert, wie es fuer die genannten Zwecke erforderlich ist oder
          gesetzliche Aufbewahrungsfristen bestehen. Revisionssichere Berechnungs- und Auditdaten koennen laenger
          gespeichert werden, soweit dies fuer Nachvollziehbarkeit und Compliance erforderlich ist.
        </p>
        <ul className="list-disc space-y-2 pl-5">
          <li>Kontodaten: bis zur Loeschung des Kontos zuzueglich gesetzlicher Fristen</li>
          <li>Audit- und Berechnungsprotokolle: gemaess interner Aufbewahrungsrichtlinie [vor Live definieren]</li>
          <li>Abrechnungsdaten: gemaess handels- und steuerrechtlichen Vorgaben</li>
        </ul>
      </LegalSection>

      <LegalSection title="Ihre Rechte">
        <p>Sie haben gegenueber dem Verantwortlichen folgende Rechte:</p>
        <ul className="list-disc space-y-2 pl-5">
          <li>Auskunft (Art. 15 DSGVO)</li>
          <li>Berichtigung (Art. 16 DSGVO)</li>
          <li>Loeschung (Art. 17 DSGVO)</li>
          <li>Einschraenkung der Verarbeitung (Art. 18 DSGVO)</li>
          <li>Datenuebertragbarkeit (Art. 20 DSGVO)</li>
          <li>Widerspruch (Art. 21 DSGVO)</li>
          <li>Widerruf erteilter Einwilligungen (Art. 7 Abs. 3 DSGVO)</li>
        </ul>
        <p>
          Beschwerden koennen bei einer Datenschutz-Aufsichtsbehoerde eingereicht werden. Zustaendig ist in der Regel die
          Behoerde am Sitz des Verantwortlichen.
        </p>
      </LegalSection>

      <LegalSection title="Pflicht zur Bereitstellung">
        <p>
          Die Bereitstellung bestimmter Daten ist fuer die Nutzung der Plattform erforderlich (z. B. E-Mail fuer das
          Konto). Ohne diese Daten koennen einzelne Funktionen nicht bereitgestellt werden.
        </p>
      </LegalSection>

      <LegalSection title="Automatisierte Entscheidungen">
        <p>
          GridCheck unterstuetzt fachliche Entscheidungen durch regelbasierte und teils KI-gestuetzte Auswertungen. Es
          findet keine automatisierte Entscheidung im Sinne von Art. 22 DSGVO statt, die rechtliche Wirkung gegenueber
          Nutzern entfaltet. Ergebnisse sind stets als vorlaeufige Diagnose gekennzeichnet.
        </p>
      </LegalSection>

      <LegalSection title="Kontakt Datenschutz">
        <p>
          Anfragen richten Sie bitte an:{" "}
          <a href={`mailto:${legalCompany.privacyEmail}`} className="text-brand-cyan hover:underline">
            {legalCompany.privacyEmail}
          </a>
        </p>
        <p className="text-text-dim">Stand: [Datum vor Live eintragen]</p>
      </LegalSection>
    </LegalPageShell>
  );
}
