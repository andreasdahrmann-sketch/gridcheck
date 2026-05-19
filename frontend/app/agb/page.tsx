import type { Metadata } from "next";
import { LegalPageShell, LegalSection, PlaceholderNotice } from "@/components/layout/LegalPageShell";
import { legalCompany } from "@/lib/legal";

export const metadata: Metadata = {
  title: "AGB | GridCheck",
  description: "Allgemeine Geschaeftsbedingungen fuer die Nutzung von GridCheck",
};

export default function AgbPage() {
  return (
    <LegalPageShell
      badge="Rechtliches"
      title="Allgemeine Geschaeftsbedingungen (AGB)"
      intro="Rahmenbedingungen fuer die Nutzung der GridCheck Plattform. Vor Live-Betrieb juristisch pruefen und an Ihr Angebotsmodell anpassen."
    >
      <PlaceholderNotice />

      <LegalSection title="Geltungsbereich">
        <p>
          Diese AGB regeln die Nutzung der GridCheck Plattform ({legalCompany.name}, {legalCompany.legalForm}) durch
          Unternehmerinnen, Unternehmer und – soweit zulaessig – Verbraucherinnen und Verbraucher. Abweichende
          Bedingungen der Nutzer gelten nur bei ausdruecklicher schriftlicher Zustimmung.
        </p>
        <p>
          Kontakt:{" "}
          <a href={`mailto:${legalCompany.contactEmail}`} className="text-brand-cyan hover:underline">
            {legalCompany.contactEmail}
          </a>
        </p>
      </LegalSection>

      <LegalSection title="Leistungsbeschreibung">
        <p>
          GridCheck stellt Software zur <strong className="text-white">vorlaeufigen Netzanschluss-Diagnostik</strong>,
          Datenquellenbewertung, Reporting und Entscheidungsvorbereitung bereit. Der konkrete Funktionsumfang richtet
          sich nach dem gebuchten Paket (z. B. Self-Serve, Professional, VNB Pilot).
        </p>
        <p>
          Es wird ausdruecklich kein verbindlicher Netzanschluss, keine Kapazitaetsgarantie und keine Ersatzpruefung
          durch den Netzbetreiber geschuldet.
        </p>
      </LegalSection>

      <LegalSection title="Registrierung und Konto">
        <p>
          Nutzer sind verpflichtet, Zugangsdaten geheim zu halten und Zutritte Dritter zu unterbinden. Der Anbieter darf
          Konten bei Missbrauch, Sicherheitsrisiken oder Verstoss gegen diese AGB sperren.
        </p>
      </LegalSection>

      <LegalSection title="Nutzungspflichten">
        <ul className="list-disc space-y-2 pl-5">
          <li>Eingaben wahrheitsgemaess und im Rahmen berechtigter Zwecke verwenden</li>
          <li>Keine rechtswidrigen, sensiblen oder unbefugten Infrastrukturdaten hochladen</li>
          <li>Ergebnisse nicht als verbindliche Netzbetreiber-Zusage darstellen</li>
          <li>Automatisierte Zugriffe nur im vereinbarten Umfang (API-Limits, Fair Use)</li>
        </ul>
      </LegalSection>

      <LegalSection title="Preise und Zahlung">
        <p>
          Preise verstehen sich – sofern nicht anders angegeben – zzgl. gesetzlicher Umsatzsteuer. Abonnements und
          Einzelprojekte werden ueber den jeweils angegebenen Zahlungsweg abgerechnet. Details zu Laufzeit, Verlaengerung
          und Kuendigung ergeben sich aus dem Checkout bzw. der Produktbeschreibung.
        </p>
        <p className="text-text-dim">[Konkrete Zahlungs- und Kuendigungsfristen vor Live ergaenzen]</p>
      </LegalSection>

      <LegalSection title="Verfuegbarkeit und Wartung">
        <p>
          Der Anbieter betreibt die Plattform nach dem Stand der Technik. Wartungsfenster, Stoerungen und
          Weiterentwicklungen koennen die Verfuegbarkeit voruebergehend einschraenken. Kein Anspruch auf ununterbrochene
          Verfuegbarkeit, sofern nicht individuell vereinbart.
        </p>
      </LegalSection>

      <LegalSection title="Haftung">
        <p>
          Der Anbieter haftet unbeschraenkt bei Vorsatz und grober Fahrlaessigkeit sowie bei Verletzung von Leben,
          Koerper oder Gesundheit. Bei leichter Fahrlaessigkeit haftet der Anbieter nur bei Verletzung wesentlicher
          Vertragspflichten und begrenzt auf den vorhersehbaren, typischen Schaden.
        </p>
        <p>
          Fuer Entscheidungen auf Basis vorlaeufiger Analysen traegt die nutzende Organisation die fachliche Pruefung und
          Abstimmung mit dem Netzbetreiber.
        </p>
      </LegalSection>

      <LegalSection title="Schlussbestimmungen">
        <p>Es gilt deutsches Recht unter Ausschluss des UN-Kaufrechts, soweit zulaessig.</p>
        <p>
          Gerichtsstand fuer Kaufleute ist – soweit zulaessig – [Sitz des Anbieters]. Verbraucher behalten gesetzliche
          Zustaendigkeiten.
        </p>
        <p>Stand: [Datum vor Live eintragen]</p>
      </LegalSection>
    </LegalPageShell>
  );
}
