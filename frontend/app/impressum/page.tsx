import type { Metadata } from "next";
import { LegalPageShell, LegalSection, PlaceholderNotice } from "@/components/layout/LegalPageShell";

export const metadata: Metadata = {
  title: "Impressum | GridCheck",
  description: "Anbieterkennzeichnung und Kontakt der GridCheck Plattform",
};

export default function ImpressumPage() {
  return (
    <LegalPageShell
      badge="Rechtliches"
      title="Impressum"
      intro="Pflichtangaben gemaess § 5 TMG und § 18 MStV fuer den Betrieb der GridCheck Plattform."
    >
      <PlaceholderNotice />

      <LegalSection title="Anbieter">
        <p>
          <strong className="text-white">[Firmenname – Platzhalter]</strong>
          <br />
          [Rechtsform, z. B. GmbH]
          <br />
          [Strasse und Hausnummer]
          <br />
          [PLZ Ort], Deutschland
        </p>
        <p>Vertreten durch: [Geschaeftsfuehrung / vertretungsberechtigte Person]</p>
        <p>Registergericht: [Amtsgericht] · Registernummer: [HRB …]</p>
        <p>Umsatzsteuer-ID: [DE…] (falls vorhanden)</p>
      </LegalSection>

      <LegalSection title="Kontakt">
        <p>
          E-Mail:{" "}
          <a href="mailto:kontakt@example.com" className="text-brand-cyan hover:underline">
            kontakt@example.com
          </a>
        </p>
        <p>Telefon: [+49 …] (optional)</p>
        <p>Supportzeiten: [Werktags, Zeitfenster – Platzhalter]</p>
      </LegalSection>

      <LegalSection title="Verantwortlich fuer den Inhalt (§ 18 Abs. 2 MStV)">
        <p>[Name, Anschrift wie oben oder abweichende ladungsfaehige Anschrift]</p>
      </LegalSection>

      <LegalSection title="Haftungsausschluss (vorlaeufige Analyse)">
        <p>
          GridCheck stellt eine <strong className="text-white">vorlaeufige, erklaerende Netzanschluss-Diagnostik</strong>{" "}
          bereit. Ergebnisse basieren auf den eingegebenen Projektdaten, oeffentlichen und modellierten Quellen sowie
          dokumentierten Annahmen.
        </p>
        <p>
          Es wird <strong className="text-white">keine verbindliche Netzanschlusszusage</strong>, keine Garantie freier
          Netzkapazitaet und keine Ersatzpruefung durch den zustaendigen Netzbetreiber erbracht. Verbindliche
          Entscheidungen obliegen ausschliesslich dem zustaendigen Netz- bzw. Verteilnetzbetreiber.
        </p>
        <p>
          Trotz sorgfaeltiger Aufbereitung koennen Daten unvollstaendig, veraltet oder regional unterschiedlich sein.
          Nutzerinnen und Nutzer sind verpflichtet, Ergebnisse fachlich zu pruefen, bevor sie investitions- oder
          antragsrelevante Entscheidungen treffen.
        </p>
      </LegalSection>

      <LegalSection title="Streitbeilegung">
        <p>
          Die Europaeische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{" "}
          <a
            href="https://ec.europa.eu/consumers/odr"
            className="text-brand-cyan hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            https://ec.europa.eu/consumers/odr
          </a>
          . Wir sind nicht verpflichtet und nicht bereit, an Streitbeilegungsverfahren vor einer
          Verbraucherschlichtungsstelle teilzunehmen, sofern nicht gesetzlich anders vorgeschrieben.
        </p>
      </LegalSection>
    </LegalPageShell>
  );
}
