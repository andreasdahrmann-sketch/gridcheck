"use client";

import type { GridCheckResult } from "@/types";
import {
  buildConfidenceHighlights,
  getConfidenceLevelMeta,
  type ConfidenceTone,
} from "@/lib/confidence-display";

const TONE_STYLES: Record<ConfidenceTone, { panel: string; badge: string }> = {
  strong: {
    panel: "border-emerald-400/30 bg-emerald-500/10",
    badge: "bg-emerald-500/20 text-emerald-100",
  },
  moderate: {
    panel: "border-sky-400/30 bg-sky-500/10",
    badge: "bg-sky-500/20 text-sky-100",
  },
  weak: {
    panel: "border-amber-400/30 bg-amber-500/10",
    badge: "bg-amber-500/20 text-amber-100",
  },
  unknown: {
    panel: "border-orange-400/30 bg-orange-500/10",
    badge: "bg-orange-500/20 text-orange-100",
  },
};

function fmtPercent(value: number) {
  return `${Math.round(value)} %`;
}

interface ConfidenceSummaryPanelProps {
  result: GridCheckResult;
  className?: string;
}

export default function ConfidenceSummaryPanel({ result, className = "" }: ConfidenceSummaryPanelProps) {
  const dataMeta = getConfidenceLevelMeta(result.daten_confidence);
  const tone = TONE_STYLES[dataMeta.tone];
  const highlights = buildConfidenceHighlights(result);
  const kiPercent = Number.isFinite(result.ki.konfidenz_prozent) ? result.ki.konfidenz_prozent : result.konfidenz;

  return (
    <section
      className={`rounded-2xl border p-5 md:p-6 ${tone.panel} ${className}`}
      aria-labelledby="confidence-summary-heading"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-300">Daten-Confidence</p>
          <h3 id="confidence-summary-heading" className="mt-2 text-xl font-bold text-white md:text-2xl">
            {dataMeta.label}
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-200">{dataMeta.summary}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${tone.badge}`}>
            Datenklasse {result.daten_confidence}
          </span>
          <span className="rounded-full border border-white/15 bg-black/20 px-3 py-1 text-xs font-semibold text-white">
            KI-Kalibrierung {fmtPercent(kiPercent)}
          </span>
          {result.n1.n1_klasse ? (
            <span className="rounded-full border border-white/15 bg-black/20 px-3 py-1 text-xs font-semibold text-white">
              N-1 {result.n1.n1_klasse}
            </span>
          ) : null}
        </div>
      </div>

      {highlights.length > 0 ? (
        <div className="mt-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Wesentliche Annahmen & Hinweise</p>
          <ul className="mt-2 space-y-2 text-sm leading-6 text-gray-200">
            {highlights.map((item, index) => (
              <li key={index} className="flex gap-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-white/70" aria-hidden />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-gray-400">
            Vollständige Transparenz, Disclaimer und weitere Confidence-Hinweise stehen weiter unten im Abschnitt
            „Transparenz / Annahmen“.
          </p>
        </div>
      ) : null}
    </section>
  );
}
