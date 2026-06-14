import type { Metadata } from "next";
import { LegalPageShell, LegalSection } from "@/components/layout/LegalPageShell";
import { LEGAL_DATA, renderLegalText } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Impressum | GridCheck",
  description: "Anbieterkennzeichnung und Pflichtangaben gemaess § 5 TMG / § 18 MStV",
};

export default function ImpressumPage() {
  return (
    <LegalPageShell
      badge="Rechtliches"
      title="Impressum"
      intro="Anbieterkennzeichnung gemaess § 5 TMG sowie verantwortliche Stelle gemaess § 18 Abs. 2 MStV."
    >
      <LegalSection title="Anbieter (§ 5 TMG)">
        <p className="whitespace-pre-line">
          <strong className="text-white">{LEGAL_DATA.FIRMA_NAME}</strong>
          {"\n"}
          {renderLegalText("{{RECHTSFORM}}")}
          {"\n"}
          {renderLegalText("{{STRASSE_HAUSNR}}")}
          {"\n"}
          {renderLegalText("{{PLZ_ORT}}")}
          {"\n"}
          {renderLegalText("{{LAND}}")}
        </p>
        <p>
          <strong className="text-white">Vertretungsberechtigt:</strong> {renderLegalText("{{GESCHAEFTSFUEHRER}}")}
        </p>
        <p>
          <strong className="text-white">Registergericht:</strong> {renderLegalText("{{REGISTERGERICHT}}")}
          <br />
          <strong className="text-white">Registernummer:</strong> {renderLegalText("{{HRB_NR}}")}
        </p>
      </LegalSection>

      <LegalSection title="Kontakt">
        <p>
          E-Mail:{" "}
          <a
            href={`mailto:${LEGAL_DATA.KONTAKT_EMAIL}`}
            className="text-brand-cyan hover:underline"
          >
            {LEGAL_DATA.KONTAKT_EMAIL}
          </a>
        </p>
        <p>Telefon: {renderLegalText("{{TELEFON}}")}</p>
      </LegalSection>

      <LegalSection title="Umsatzsteuer (§ 27a UStG)">
        <p>
          Umsatzsteuer-Identifikationsnummer gemaess § 27a Umsatzsteuergesetz:
          <br />
          {renderLegalText("{{USTID}}")}
        </p>
      </LegalSection>

      <LegalSection title="Verantwortlich fuer den Inhalt (§ 18 Abs. 2 MStV)">
        <p>
          {renderLegalText("{{GESCHAEFTSFUEHRER}}")}
          <br />
          {renderLegalText("{{FIRMA_NAME}}")}
          <br />
          {renderLegalText("{{STRASSE_HAUSNR}}")}, {renderLegalText("{{PLZ_ORT}}")}
        </p>
      </LegalSection>

      <LegalSection title="EU-Streitschlichtung / Verbraucherstreitbeilegung">
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
          . Unsere E-Mail-Adresse finden Sie oben im Impressum.
        </p>
        <p>
          <strong className="text-white">Verbraucherstreitbeilegung / Universalschlichtungsstelle:</strong>{" "}
          Wir sind nicht bereit oder verpflichtet, an Streitbeilegungsverfahren vor einer
          Verbraucherschlichtungsstelle teilzunehmen, sofern nicht gesetzlich anders vorgeschrieben
          (§ 36 VSBG).
        </p>
      </LegalSection>

      <LegalSection title="Haftung fuer Inhalte">
        <p>
          Als Diensteanbieter sind wir gemaess § 7 Abs. 1 TMG fuer eigene Inhalte auf diesen Seiten
          nach den allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 TMG sind wir als
          Diensteanbieter jedoch nicht verpflichtet, uebermittelte oder gespeicherte fremde
          Informationen zu ueberwachen oder nach Umstaenden zu forschen, die auf eine rechtswidrige
          Taetigkeit hinweisen. Verpflichtungen zur Entfernung oder Sperrung der Nutzung von
          Informationen nach den allgemeinen Gesetzen bleiben hiervon unberuehrt. Eine diesbezuegliche
          Haftung ist erst ab dem Zeitpunkt der Kenntnis einer konkreten Rechtsverletzung moeglich.
        </p>
        <p>
          GridCheck stellt eine{" "}
          <strong className="text-white">vorlaeufige, erklaerende Netzanschluss-Diagnostik</strong>{" "}
          bereit. Es wird <strong className="text-white">keine verbindliche Netzanschlusszusage</strong>,
          keine Garantie freier Netzkapazitaet und keine Ersatzpruefung durch den zustaendigen
          Netzbetreiber erbracht. Verbindliche Entscheidungen obliegen ausschliesslich dem
          zustaendigen Netz- bzw. Verteilnetzbetreiber. Oeffentliche Daten koennen unvollstaendig
          oder veraltet sein.
        </p>
      </LegalSection>

      <LegalSection title="Haftung fuer Links">
        <p>
          Unser Angebot enthaelt Links zu externen Webseiten Dritter, auf deren Inhalte wir keinen
          Einfluss haben. Deshalb koennen wir fuer diese fremden Inhalte auch keine Gewaehr
          uebernehmen. Fuer die Inhalte der verlinkten Seiten ist stets der jeweilige Anbieter oder
          Betreiber der Seiten verantwortlich. Die verlinkten Seiten wurden zum Zeitpunkt der
          Verlinkung auf moegliche Rechtsverstoesse ueberprueft. Eine permanente inhaltliche
          Kontrolle der verlinkten Seiten ist ohne konkrete Anhaltspunkte einer Rechtsverletzung
          nicht zumutbar. Bei Bekanntwerden von Rechtsverletzungen werden wir derartige Links
          umgehend entfernen.
        </p>
      </LegalSection>

      <LegalSection title="Urheberrecht">
        <p>
          Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen
          dem deutschen Urheberrecht. Die Vervielfaeltigung, Bearbeitung, Verbreitung und jede Art
          der Verwertung ausserhalb der Grenzen des Urheberrechts beduerfen der schriftlichen
          Zustimmung des jeweiligen Autors bzw. Erstellers. Downloads und Kopien dieser Seite sind
          nur fuer den privaten, nicht kommerziellen Gebrauch gestattet.
        </p>
        <p>
          Soweit die Inhalte auf dieser Seite nicht vom Betreiber erstellt wurden, werden die
          Urheberrechte Dritter beachtet. Insbesondere werden Inhalte Dritter als solche
          gekennzeichnet. Geodaten und Kartenmaterial koennen u. a. von OpenStreetMap-Mitwirkenden
          stammen (Lizenz: ODbL).
        </p>
      </LegalSection>
    </LegalPageShell>
  );
}
