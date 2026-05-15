/**
 * Statische Textbausteine (DE) für PDF/HTML-Renderer.
 * Platzhalter: {name} — siehe fillReportTemplate.
 */

export const sharedDisclaimerDe = `Diese Analyse ist eine vorläufige technische und wirtschaftliche Einschätzung auf Basis verfügbarer Daten, Modellannahmen und öffentlicher Quellen.
Sie stellt keine verbindliche Netzanschlusszusage, keine Kapazitätsbestätigung und keine abschließende Netzberechnung dar.
Die finale technische und rechtliche Bewertung erfolgt ausschließlich durch den zuständigen Netzbetreiber oder durch hierzu beauftragte Fachplaner mit vollständigen Netzdaten.`;

export const projectDeveloperConclusionTemplate = `Der betrachtete Standort ist aus Netzanschlusssicht {recommendationText}.
Die geplante Leistung von {feedInCapacityMw} MW liegt nach aktuellem Screening im Bereich {riskText}.
Für die weitere Projektentwicklung sollten insbesondere die Anschlussvarianten {topCandidateLabels} vertieft betrachtet werden.`;

export const gridOperatorReviewNoteTemplate = `Die vorliegende Analyse dient der strukturierten Vorprüfung einer Netzanschlussanfrage.
Eine abschließende Bewertung der Netzverträglichkeit ist auf Basis der verfügbaren Daten nicht möglich.
Für eine belastbare Prüfung sind interne Netzmodelle, Betriebsmitteldaten, Last-/Einspeisesituationen sowie Schutz- und Schaltzustände erforderlich.`;

export const investorExecutiveSummaryTemplate = `Das Projekt wird aus Netzanschlusssicht aktuell als {investmentConclusion} eingestuft.
Die wesentlichen wertrelevanten Risiken liegen in {mainRiskDrivers}.
Für eine Investmententscheidung sollten CAPEX-Puffer, Zeitplanrisiken und mögliche Einspeisebegrenzungen berücksichtigt werden.`;

const PLACEHOLDER = /\{(\w+)\}/g;

export function fillReportTemplate(
  template: string,
  vars: Record<string, string | number | undefined>,
): string {
  return template.replace(PLACEHOLDER, (_match, key: string) => {
    const v = vars[key];
    if (v === undefined || v === null || v === "") {
      return `{${key}}`;
    }
    return String(v);
  });
}
