import type { Metadata } from "next";
import { LegalPageShell, LegalSection } from "@/components/layout/LegalPageShell";
import {
  DATA_PROCESSORS,
  LEGAL_DATA,
  activeDataProcessors,
  renderLegalText,
} from "@/lib/legal";

export const metadata: Metadata = {
  title: "Datenschutzerklaerung | GridCheck",
  description: "Hinweise nach Art. 13 DSGVO zur Verarbeitung personenbezogener Daten in der GridCheck-Plattform",
};

const TRANSFER_BASIS_LABEL: Record<string, string> = {
  EU_EWR: "EU/EWR",
  SCC: "Drittland (Standardvertragsklauseln)",
  SCC_DPF: "USA (Standardvertragsklauseln + EU-US Data Privacy Framework)",
  ADEQUACY: "Drittland mit Angemessenheitsbeschluss",
};

export default function DatenschutzPage() {
  const active = activeDataProcessors();
  const inactive = DATA_PROCESSORS.filter((p) => !p.active);

  return (
    <LegalPageShell
      badge="Rechtliches"
      title="Datenschutzerklaerung"
      intro="Informationen gemaess Art. 13 / 14 DSGVO zur Verarbeitung personenbezogener Daten im Rahmen der GridCheck-Plattform."
    >
      <LegalSection title="1. Verantwortlicher (Art. 4 Nr. 7 DSGVO)">
        <p className="whitespace-pre-line">
          <strong className="text-white">{LEGAL_DATA.FIRMA_NAME}</strong>
          {"\n"}
          {renderLegalText("{{RECHTSFORM}}")}
          {"\n"}
          {renderLegalText("{{STRASSE_HAUSNR}}")}
          {"\n"}
          {renderLegalText("{{PLZ_ORT}}")}, {renderLegalText("{{LAND}}")}
        </p>
        <p>
          E-Mail:{" "}
          <a href={`mailto:${LEGAL_DATA.KONTAKT_EMAIL}`} className="text-brand-cyan hover:underline">
            {LEGAL_DATA.KONTAKT_EMAIL}
          </a>
          <br />
          Telefon: {renderLegalText("{{TELEFON}}")}
        </p>
        <p>
          Vertretungsberechtigt: {renderLegalText("{{GESCHAEFTSFUEHRER}}")}
        </p>
      </LegalSection>

      <LegalSection title="2. Datenschutzbeauftragte/r (Art. 37 DSGVO)">
        <p>
          {renderLegalText("{{DPO_NAME}}")}
          <br />
          E-Mail:{" "}
          <a href={`mailto:${LEGAL_DATA.DPO_EMAIL}`} className="text-brand-cyan hover:underline">
            {LEGAL_DATA.DPO_EMAIL}
          </a>
        </p>
        <p className="text-xs text-text-dim">
          Hinweis: Eine gesetzliche Pflicht zur Bestellung eines Datenschutzbeauftragten besteht
          gemaess § 38 BDSG ab definierten Schwellen. Soweit (noch) nicht bestellt, dient die
          oben angegebene Adresse als zentraler Datenschutz-Kontakt.
        </p>
      </LegalSection>

      <LegalSection title="3. Zwecke und Rechtsgrundlagen (Art. 6 DSGVO)">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong className="text-white">Bereitstellung der Plattform, Konten, Analysen, Reports:</strong>{" "}
            Art. 6 Abs. 1 lit. b DSGVO (Vertragserfuellung / vorvertragliche Massnahmen).
          </li>
          <li>
            <strong className="text-white">Sicherheit, Missbrauchspraevention, Logging, Stabilitaets-Monitoring:</strong>{" "}
            Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an einem sicheren, stabilen Betrieb).
          </li>
          <li>
            <strong className="text-white">Gesetzliche Aufbewahrungs-, Buchhaltungs- und Nachweispflichten:</strong>{" "}
            Art. 6 Abs. 1 lit. c DSGVO i.V.m. § 257 HGB / § 147 AO.
          </li>
          <li>
            <strong className="text-white">Optionale Reichweitenmessung, Marketing-Cookies, Newsletter:</strong>{" "}
            Art. 6 Abs. 1 lit. a DSGVO (Einwilligung, jederzeit widerruflich) i.V.m.
            TTDSG § 25.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="4. Datenkategorien">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong className="text-white">Account-Daten:</strong> E-Mail-Adresse, Passwort-Hash
            (bcrypt), Rolle, Organisation.
          </li>
          <li>
            <strong className="text-white">Projekt- und Fachdaten:</strong> Standortangaben (Adresse,
            Koordinaten), Projektart, Projektleistung, technische Eingaben, Annahmen,
            Ergebnisdaten.
          </li>
          <li>
            <strong className="text-white">Nutzungs- und Sicherheitsdaten:</strong> IP-Adresse,
            User-Agent, Zeitstempel, Anmelde- und Sicherheitsereignisse, Fehler-Logs.
          </li>
          <li>
            <strong className="text-white">Audit- und Revisionsdaten:</strong> Hash-Chain pro
            Berechnung, App-/Norm-Version, User-/Projekt-Bezug — gesetzliche und vertragliche
            Nachweisbarkeit (siehe ADR-005, ADR-008).
          </li>
          <li>
            <strong className="text-white">Abrechnungsdaten:</strong> Paketwahl, Zahlungsstatus,
            Rechnungs-Stammdaten (eigentliche Zahlungsdaten beim Zahlungsdienstleister).
          </li>
          <li>
            <strong className="text-white">Kommunikationsdaten:</strong> Support-Anfragen,
            Passwort-Reset.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="5. Empfaenger / Auftragsverarbeiter (Art. 28 DSGVO)">
        <p>
          Wir setzen sorgfaeltig ausgewaehlte Auftragsverarbeiter ein. Mit allen Auftragsverarbeitern
          bestehen Vertraege gemaess Art. 28 DSGVO (AVV / DPA). Verarbeitungen ausserhalb der EU/EWR
          erfolgen nur auf Grundlage geeigneter Garantien (Standardvertragsklauseln nach Art. 46
          DSGVO und/oder EU-US Data Privacy Framework).
        </p>
        <div className="overflow-x-auto">
          <table className="mt-2 w-full min-w-[640px] table-auto text-left text-xs">
            <thead className="border-b border-white/10 text-text-muted">
              <tr>
                <th className="py-2 pr-3 font-semibold">Anbieter</th>
                <th className="py-2 pr-3 font-semibold">Zweck</th>
                <th className="py-2 pr-3 font-semibold">Sitz / Transfer</th>
                <th className="py-2 pr-3 font-semibold">Rechtsgrundlage</th>
                <th className="py-2 pr-3 font-semibold">AVV</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {active.map((p) => (
                <tr key={p.name} className="align-top">
                  <td className="py-2 pr-3 font-medium text-white">
                    {p.vendorPrivacyUrl ? (
                      <a
                        href={p.vendorPrivacyUrl}
                        className="text-brand-cyan hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {p.name}
                      </a>
                    ) : (
                      p.name
                    )}
                  </td>
                  <td className="py-2 pr-3 text-text-muted">{p.purpose}</td>
                  <td className="py-2 pr-3 text-text-muted">
                    {p.location}
                    <br />
                    <span className="text-text-dim">{TRANSFER_BASIS_LABEL[p.transferBasis]}</span>
                  </td>
                  <td className="py-2 pr-3 text-text-muted">{p.legalBasis}</td>
                  <td className="py-2 pr-3 text-text-muted">{p.dpaSigned ? "Ja" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {inactive.length > 0 && (
          <p className="text-xs text-text-dim">
            Folgende Anbieter sind <strong className="text-text-muted">aktuell nicht aktiv</strong>{" "}
            eingebunden und werden erst nach Aktivierung und ggf. Einwilligung verarbeitet:{" "}
            {inactive.map((p) => p.name).join(", ")}.
          </p>
        )}
      </LegalSection>

      <LegalSection title="6. Drittlandsuebermittlung (Art. 44 ff. DSGVO)">
        <p>
          Eine Uebermittlung in Drittlaender ausserhalb der EU/EWR erfolgt nur, wenn ein
          Angemessenheitsbeschluss (Art. 45 DSGVO) oder geeignete Garantien (Art. 46 DSGVO)
          vorliegen. Konkret nutzen wir fuer US-Anbieter (z. B. Vercel, ggf. Stripe, ggf. Sentry)
          die EU-Standardvertragsklauseln (SCC) in Verbindung mit dem EU-US Data Privacy Framework
          (Angemessenheitsbeschluss vom 10.07.2023). Geocoding-Anfragen an OpenStreetMap/Nominatim
          werden gegenueber einer EU/UK-basierten Stiftung verarbeitet.
        </p>
      </LegalSection>

      <LegalSection title="7. Speicherdauer">
        <p>
          Personenbezogene Daten werden nur so lange gespeichert, wie es fuer die jeweiligen Zwecke
          erforderlich ist oder gesetzliche Aufbewahrungs- und Nachweispflichten dies verlangen.
        </p>
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong className="text-white">Konto-Stammdaten:</strong> bis zur Loeschung des Kontos
            zuzueglich gesetzlicher Fristen. Loeschungen erfolgen ueber Soft-Delete
            (`deleted_at`), bleiben aber fuer Audit- und Revisionszwecke sperrgespeichert.
          </li>
          <li>
            <strong className="text-white">Projektdaten:</strong> bis zur Loeschung des zugehoerigen
            Projekts (Soft-Delete) zuzueglich Aufbewahrungsfrist fuer Audit-Trail.
          </li>
          <li>
            <strong className="text-white">Audit- / Berechnungs-Hash-Chain:</strong> revisionssicher,
            append-only — Aufbewahrung gemaess vertraglicher und gesetzlicher Anforderungen
            (typischerweise mind. 6 bzw. 10 Jahre, soweit handels-/steuerrechtlich relevant).
          </li>
          <li>
            <strong className="text-white">Abrechnungs- und Buchhaltungsdaten:</strong> 10 Jahre
            (§ 257 HGB, § 147 AO).
          </li>
          <li>
            <strong className="text-white">Server-/Sicherheits-Logs:</strong> in der Regel 30–90
            Tage, laenger nur bei Sicherheitsvorfaellen.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="8. Ihre Rechte (Art. 15–22, 7, 77 DSGVO)">
        <ul className="list-disc space-y-2 pl-5">
          <li>Auskunft ueber gespeicherte Daten (Art. 15 DSGVO)</li>
          <li>Berichtigung unrichtiger Daten (Art. 16 DSGVO)</li>
          <li>Loeschung (Art. 17 DSGVO), soweit keine Aufbewahrungspflicht entgegensteht</li>
          <li>Einschraenkung der Verarbeitung (Art. 18 DSGVO)</li>
          <li>Datenuebertragbarkeit (Art. 20 DSGVO)</li>
          <li>Widerspruch gegen Verarbeitungen auf Grundlage berechtigter Interessen (Art. 21 DSGVO)</li>
          <li>
            Widerruf erteilter Einwilligungen mit Wirkung fuer die Zukunft (Art. 7 Abs. 3 DSGVO) —
            insbesondere fuer Cookie-/Tracking-Einwilligungen ueber das Consent-Banner
          </li>
          <li>
            Beschwerde bei einer Datenschutz-Aufsichtsbehoerde (Art. 77 DSGVO). Zustaendig ist
            insbesondere die Aufsichtsbehoerde am Sitz des Verantwortlichen:{" "}
            {renderLegalText("{{AUFSICHTSBEHOERDE}}")}.
          </li>
        </ul>
        <p>
          Anfragen zu Ihren Rechten richten Sie bitte an{" "}
          <a href={`mailto:${LEGAL_DATA.DPO_EMAIL}`} className="text-brand-cyan hover:underline">
            {LEGAL_DATA.DPO_EMAIL}
          </a>
          .
        </p>
      </LegalSection>

      <LegalSection title="9. Cookies, lokale Speicherung und Tracking (TTDSG § 25)">
        <p>
          Wir setzen technisch notwendige Cookies / lokale Speicher ein, um Anmeldung, Sicherheit,
          CSRF-Schutz und grundlegende UI-Praeferenzen zu ermoeglichen. Diese werden ohne
          Einwilligung verarbeitet (TTDSG § 25 Abs. 2 Nr. 2 / Art. 6 Abs. 1 lit. b DSGVO).
        </p>
        <p>
          Optionale Cookies / Tracker fuer Reichweitenmessung oder Marketing setzen wir{" "}
          <strong className="text-white">ausschliesslich nach Ihrer ausdruecklichen Einwilligung</strong>{" "}
          ueber das Consent-Banner ein. Vor erteilter Einwilligung wird kein nicht-essenzieller
          Cookie / Tracker geladen. Sie koennen Ihre Einwilligung jederzeit ueber die
          Cookie-Einstellungen widerrufen.
        </p>
      </LegalSection>

      <LegalSection title="10. Automatisierte Entscheidungsfindung / Profiling (Art. 22 DSGVO)">
        <p>
          Eine ausschliesslich automatisierte Entscheidung im Sinne des Art. 22 DSGVO, die
          rechtliche Wirkung gegenueber den Nutzern entfaltet oder sie aehnlich erheblich
          beeintraechtigt, findet <strong className="text-white">nicht</strong> statt. GridCheck
          unterstuetzt fachliche Entscheidungen durch regelbasierte und teils KI-gestuetzte
          Auswertungen; alle Ergebnisse sind ausdruecklich als <em>vorlaeufige Diagnose</em>{" "}
          gekennzeichnet und ersetzen keine rechtsverbindliche Pruefung durch den zustaendigen
          Netzbetreiber.
        </p>
      </LegalSection>

      <LegalSection title="11. Pflicht zur Bereitstellung">
        <p>
          Die Bereitstellung bestimmter personenbezogener Daten (insbesondere E-Mail) ist fuer den
          Vertragsschluss und die Nutzung des Kontos erforderlich. Ohne diese Daten koennen die
          entsprechenden Funktionen nicht bereitgestellt werden.
        </p>
      </LegalSection>

      <LegalSection title="12. Stand und Aktualisierungen">
        <p>
          Stand dieser Datenschutzerklaerung: {renderLegalText("{{STAND_DATUM}}")}.
        </p>
        <p>
          Wir behalten uns vor, diese Datenschutzerklaerung anzupassen, um sie an geaenderte
          Rechtslagen oder bei Aenderungen der Verarbeitung anzupassen. Die jeweils aktuelle Version
          ist auf dieser Seite abrufbar.
        </p>
      </LegalSection>
    </LegalPageShell>
  );
}
