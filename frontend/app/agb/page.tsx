import type { Metadata } from "next";
import { LegalPageShell, LegalSection } from "@/components/layout/LegalPageShell";
import { LEGAL_DATA, renderLegalText } from "@/lib/legal";

export const metadata: Metadata = {
  title: "AGB | GridCheck",
  description: "Allgemeine Geschaeftsbedingungen fuer die Nutzung der GridCheck-Plattform",
};

export default function AgbPage() {
  return (
    <LegalPageShell
      badge="Rechtliches"
      title="Allgemeine Geschaeftsbedingungen (AGB)"
      intro="Vertragliche Rahmenbedingungen fuer die Nutzung der GridCheck-Plattform fuer vorlaeufige Netzanschluss-Diagnostik."
    >
      <LegalSection title="1. Geltungsbereich und Vertragspartner">
        <p>
          Diese Allgemeinen Geschaeftsbedingungen (nachfolgend „AGB“) regeln die Nutzung der
          SaaS-Plattform GridCheck (nachfolgend „Plattform“) zwischen
        </p>
        <p className="whitespace-pre-line">
          <strong className="text-white">{LEGAL_DATA.FIRMA_NAME}</strong>
          {"\n"}
          {renderLegalText("{{RECHTSFORM}}")}
          {"\n"}
          {renderLegalText("{{STRASSE_HAUSNR}}")}, {renderLegalText("{{PLZ_ORT}}")}, {renderLegalText("{{LAND}}")}
          {"\n"}
          (nachfolgend „Anbieter“)
        </p>
        <p>und der jeweiligen Nutzerin / dem jeweiligen Nutzer (nachfolgend „Nutzer“).</p>
        <p>
          Die Plattform richtet sich primaer an Unternehmer im Sinne des § 14 BGB (Projektentwickler,
          Planungsbueros, Netzbetreiber, Investoren, Kommunen). Soweit Verbraucher (§ 13 BGB) die
          Plattform nutzen koennen, gelten zwingende Verbraucherschutzvorschriften ergaenzend.
        </p>
        <p>
          Abweichende, entgegenstehende oder ergaenzende Bedingungen des Nutzers werden nur dann
          Vertragsbestandteil, wenn der Anbieter ihrer Geltung ausdruecklich schriftlich zustimmt.
        </p>
      </LegalSection>

      <LegalSection title="2. Leistungsbeschreibung">
        <p>
          Die Plattform stellt eine{" "}
          <strong className="text-white">vorlaeufige Netzanschluss-Diagnostik</strong>,
          Netzkapazitaetsindikatoren, N-1-Screening, GIS-basierte Netzasset-Erkennung sowie eine
          revisionssichere Entscheidungsvorbereitung bereit.
        </p>
        <p>
          Der Anbieter weist ausdruecklich darauf hin und der Nutzer nimmt zur Kenntnis, dass es
          sich ausschliesslich um eine{" "}
          <strong className="text-white">vorlaeufige Analyse</strong> handelt. Die Plattform
          erbringt insbesondere
        </p>
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong className="text-white">keine rechtsverbindliche Netzanschlusszusage</strong>,
          </li>
          <li>
            <strong className="text-white">keine Kapazitaetsgarantie</strong> hinsichtlich freier
            Netzkapazitaeten,
          </li>
          <li>
            keine Ersatzpruefung durch den zustaendigen Netz- oder Verteilnetzbetreiber.
          </li>
        </ul>
        <p>
          Oeffentliche Daten (z. B. OpenStreetMap, Marktstammdatenregister) koennen unvollstaendig
          oder veraltet sein. Die finale Entscheidung ueber einen Netzanschluss obliegt
          ausschliesslich dem zustaendigen Netzbetreiber. Der Funktionsumfang richtet sich nach dem
          jeweils gebuchten Paket und kann sich im Rahmen der Weiterentwicklung der Plattform
          aendern, soweit dies fuer den Nutzer zumutbar ist und den Vertragszweck nicht gefaehrdet.
        </p>
      </LegalSection>

      <LegalSection title="3. Vertragsschluss">
        <p>
          Die Darstellung der Plattform-Pakete stellt kein bindendes Angebot, sondern eine
          Aufforderung zur Abgabe eines Angebots dar. Der Vertrag kommt zustande, indem der Nutzer
          sich auf der Plattform registriert oder ein Paket bestellt und der Anbieter die
          Registrierung bzw. Bestellung in Textform (z. B. per E-Mail) bestaetigt oder den Zugang
          freischaltet.
        </p>
        <p>
          Der Nutzer ist verpflichtet, bei Registrierung wahrheitsgemaesse und vollstaendige Angaben
          zu machen und seine Zugangsdaten geheim zu halten.
        </p>
      </LegalSection>

      <LegalSection title="4. Preise und Zahlungsbedingungen">
        <p>
          Es gelten die zum Zeitpunkt der Bestellung in der Plattform ausgewiesenen Preise. Soweit
          nicht anders angegeben, verstehen sich Preise gegenueber Unternehmern netto zzgl.
          gesetzlicher Umsatzsteuer.
        </p>
        <p>
          Die konkreten Zahlungsmodalitaeten (Vorab-Abrechnung, Abonnement, Einzelkauf) ergeben sich
          aus der jeweiligen Produktbeschreibung in der Plattform. Die Zahlungsabwicklung kann ueber
          externe Zahlungsdienstleister erfolgen; insoweit gelten ergaenzend deren
          Nutzungsbedingungen und Datenschutzhinweise.
        </p>
        <p>
          Bei Zahlungsverzug gelten die gesetzlichen Bestimmungen.
        </p>
      </LegalSection>

      <LegalSection title="5. Nutzungsrechte und Drittinhalte">
        <p>
          Der Anbieter raeumt dem Nutzer fuer die Dauer des Vertrags ein einfaches, nicht
          uebertragbares, nicht unterlizenzierbares Nutzungsrecht an der Plattform und an den
          erzeugten Reports / Exporten zur internen Nutzung im eigenen Geschaeftsbetrieb ein. Eine
          Weitergabe an Dritte zu kommerziellen Zwecken ist nur mit ausdruecklicher Zustimmung des
          Anbieters zulaessig.
        </p>
        <p>
          Software, Marken, Quellcode, Designs, Modelle und Texte der Plattform bleiben Eigentum
          des Anbieters bzw. der jeweiligen Rechteinhaber. Drittinhalte (insbesondere Geodaten von
          OpenStreetMap-Mitwirkenden — Lizenz: ODbL — und Daten aus dem Marktstammdatenregister bzw.
          weiteren oeffentlichen Quellen) werden im Rahmen der jeweiligen Lizenzbedingungen genutzt
          und sind als solche kenntlich gemacht.
        </p>
      </LegalSection>

      <LegalSection title="6. Pflichten des Nutzers">
        <p>Der Nutzer verpflichtet sich, insbesondere</p>
        <ul className="list-disc space-y-2 pl-5">
          <li>bei Registrierung und Eingaben wahrheitsgemaesse und vollstaendige Angaben zu machen,</li>
          <li>Zugangsdaten geheim zu halten und vor unberechtigtem Zugriff Dritter zu schuetzen,</li>
          <li>
            keine rechtswidrigen, sicherheitsrelevanten oder unbefugten Infrastrukturdaten
            hochzuladen,
          </li>
          <li>
            Ergebnisse der Plattform nicht als verbindliche Netzbetreiber-Zusage gegenueber Dritten
            darzustellen,
          </li>
          <li>
            keine Massnahmen zur Umgehung von Sicherheitsmechanismen, Zugangsbeschraenkungen oder
            API-Limits zu ergreifen,
          </li>
          <li>
            kein Reverse Engineering, Decompilieren oder Disassemblieren der Plattform vorzunehmen,
            soweit dies nicht zwingend gesetzlich erlaubt ist (§ 69e UrhG),
          </li>
          <li>
            automatisierte Zugriffe (Scraping, Bots) nur im vertraglich vereinbarten Umfang und
            unter Einhaltung der API-Bedingungen vorzunehmen.
          </li>
        </ul>
        <p>
          Der Anbieter ist berechtigt, Konten bei Verstoessen gegen diese Pflichten oder bei
          Sicherheitsrisiken vorruebergehend zu sperren oder ausserordentlich zu kuendigen.
        </p>
      </LegalSection>

      <LegalSection title="7. Haftung">
        <p>
          Der Anbieter haftet unbeschraenkt fuer Vorsatz und grobe Fahrlaessigkeit sowie fuer
          Schaeden aus der Verletzung des Lebens, des Koerpers oder der Gesundheit. Fuer einfache
          Fahrlaessigkeit haftet der Anbieter nur bei Verletzung wesentlicher Vertragspflichten
          (Kardinalpflichten); die Haftung ist in diesem Fall der Hoehe nach auf den bei
          Vertragsschluss vorhersehbaren, vertragstypischen Schaden beschraenkt.
        </p>
        <p>
          <strong className="text-white">
            Eine Haftung fuer mittelbare Schaeden, Folgeschaeden, entgangenen Gewinn, entgangene
            Einsparungen, Zins- und Finanzierungsschaeden sowie insbesondere fuer Schaeden aus
            ausgebliebenen, verzoegerten oder veraenderten Netzanschluessen, abgelehnten
            Anschlussbegehren, Redispatch-Massnahmen oder Engpass-Entscheidungen des
            Netzbetreibers ist – ausserhalb der vorstehenden Faelle unbeschraenkter Haftung – im
            gesetzlich zulaessigen Umfang ausgeschlossen.
          </strong>
        </p>
        <p>
          Die Haftung nach dem Produkthaftungsgesetz sowie aus uebernommenen Garantien bleibt
          unberuehrt. Soweit die Haftung des Anbieters ausgeschlossen oder beschraenkt ist, gilt
          dies auch fuer die persoenliche Haftung von Mitarbeitern, Vertretern und
          Erfuellungsgehilfen.
        </p>
        <p>
          Der Nutzer ist verpflichtet, die durch die Plattform erzeugten vorlaeufigen Ergebnisse
          fachlich zu pruefen und vor investitions- oder antragsrelevanten Entscheidungen mit dem
          zustaendigen Netzbetreiber abzustimmen.
        </p>
      </LegalSection>

      <LegalSection title="8. Datenschutz">
        <p>
          Die Verarbeitung personenbezogener Daten erfolgt nach Massgabe der DSGVO und der
          ergaenzenden deutschen Datenschutzgesetze. Einzelheiten ergeben sich aus der{" "}
          <a href="/datenschutz" className="text-brand-cyan hover:underline">
            Datenschutzerklaerung
          </a>
          .
        </p>
      </LegalSection>

      <LegalSection title="9. Vertragslaufzeit und Kuendigung">
        <p>
          Sofern in der Produktbeschreibung nicht ausdruecklich anders vereinbart, werden
          Abonnements auf unbestimmte Zeit geschlossen und sind monatlich zum Monatsende ordentlich
          kuendbar. Einzelkaeufe (z. B. Einzel-Reports) enden mit Erbringung der Leistung.
        </p>
        <p>
          Das Recht zur ausserordentlichen Kuendigung aus wichtigem Grund bleibt unberuehrt. Ein
          wichtiger Grund liegt fuer den Anbieter insbesondere bei erheblichem Verstoss des Nutzers
          gegen Ziffer 6 oder bei Zahlungsverzug von mehr als 30 Tagen vor.
        </p>
        <p>
          Kuendigungen beduerfen mindestens der Textform (§ 126b BGB), z. B. per E-Mail oder ueber
          die Konto-Funktion in der Plattform.
        </p>
      </LegalSection>

      <LegalSection title="10. Aenderungen der AGB">
        <p>
          Der Anbieter ist berechtigt, diese AGB mit Wirkung fuer die Zukunft zu aendern, soweit
          dies aus sachlichen Gruenden (z. B. geaenderte Rechtslage, hoechstrichterliche
          Rechtsprechung, technische Anpassungen, Erweiterung des Funktionsumfangs) erforderlich ist
          und den Nutzer nicht unangemessen benachteiligt.
        </p>
        <p>
          Aenderungen werden dem Nutzer mindestens <strong className="text-white">30 Tage vor</strong>{" "}
          ihrem geplanten Inkrafttreten in Textform mitgeteilt. Widerspricht der Nutzer der Aenderung
          nicht innerhalb von 30 Tagen ab Zugang der Mitteilung, gelten die geaenderten AGB als
          angenommen. Auf das Widerspruchsrecht und die Folgen des Schweigens wird der Nutzer in der
          Mitteilung gesondert hingewiesen. Widerspricht der Nutzer fristgerecht, ist der Anbieter
          berechtigt, den Vertrag zum Zeitpunkt des geplanten Inkrafttretens der Aenderung zu
          kuendigen.
        </p>
      </LegalSection>

      <LegalSection title="11. Schlussbestimmungen">
        <p>
          Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss des UN-Kaufrechts. Bei
          Vertraegen mit Verbrauchern gilt diese Rechtswahl nur, soweit hierdurch nicht der Schutz
          zwingender Vorschriften des Rechts des Staates entzogen wird, in dem der Verbraucher
          seinen gewoehnlichen Aufenthalt hat.
        </p>
        <p>
          Ausschliesslicher Gerichtsstand fuer alle Streitigkeiten aus oder im Zusammenhang mit
          diesem Vertrag ist – soweit der Nutzer Kaufmann, juristische Person des oeffentlichen
          Rechts oder oeffentlich-rechtliches Sondervermoegen ist –{" "}
          {renderLegalText("{{GERICHTSSTAND_ORT}}")}. Der Anbieter ist berechtigt, auch am
          allgemeinen Gerichtsstand des Nutzers zu klagen.
        </p>
        <p>
          Sollten einzelne Bestimmungen dieses Vertrags ganz oder teilweise unwirksam sein oder
          werden, beruehrt dies die Wirksamkeit der uebrigen Bestimmungen nicht. Anstelle der
          unwirksamen Bestimmung gilt diejenige wirksame Bestimmung als vereinbart, die dem
          wirtschaftlichen Zweck der unwirksamen Bestimmung am naechsten kommt. Entsprechendes gilt
          fuer Regelungsluecken.
        </p>
        <p>
          Stand: {renderLegalText("{{STAND_DATUM}}")}.
        </p>
      </LegalSection>
    </LegalPageShell>
  );
}
