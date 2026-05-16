import { AlertTriangle } from "lucide-react";

type AnalysisDisclaimerProps = {
  variant?: "banner" | "compact";
  className?: string;
};

const DISCLAIMER_TEXT =
  "Diese Analyse ist eine vorlaeufige technische und wirtschaftliche Einschaetzung auf Basis verfuegbarer Daten, Modellannahmen und oeffentlicher Quellen. Sie stellt keine verbindliche Netzanschlusszusage, keine Kapazitaetsbestaetigung und keine abschliessende Netzberechnung dar. Die finale Bewertung erfolgt ausschliesslich durch den zustaendigen Netzbetreiber.";

export function AnalysisDisclaimer({ variant = "banner", className = "" }: AnalysisDisclaimerProps) {
  if (variant === "compact") {
    return (
      <p className={`text-xs leading-5 text-text-dim ${className}`.trim()} role="note">
        {DISCLAIMER_TEXT}
      </p>
    );
  }

  return (
    <aside
      className={`rounded-2xl border border-brand-orange/25 bg-brand-orange/10 px-4 py-4 text-sm leading-6 text-text-muted ${className}`.trim()}
      role="note"
      aria-label="Rechtlicher Hinweis zur Analyse"
    >
      <p className="flex items-start gap-2 font-medium text-white">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-brand-orange" aria-hidden />
        Vorlaeufige Analyse – keine Netzanschlusszusage
      </p>
      <p className="mt-2">{DISCLAIMER_TEXT}</p>
    </aside>
  );
}
