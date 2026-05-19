"use client";

import type { GridCalculationV2 } from "@/lib/schemas/grid-calculation";
import { feasibilityStatusLabel } from "@/lib/schemas/grid-calculation";

type Props = {
  data: GridCalculationV2;
  sectionClass: string;
  sectionTitle: string;
  fmt: (value: number, digits?: number) => string;
};

export default function GridCalculationV2Panel({ data, sectionClass, sectionTitle, fmt }: Props) {
  return (
    <div className={sectionClass}>
      <h3 className={sectionTitle}>Strukturierte Vorprüfung (Engine v{data.calculation_version})</h3>
      <p className="mb-3 text-xs text-gray-500">
        Differenzierte Plausibilitätsbewertung mit dokumentierten Annahmen — keine verbindliche
        Netzanschlusszusage.
      </p>

      <div className="mb-4 rounded-lg border border-white/10 bg-gray-900/80 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Machbarkeit (ohne einfache Ampel)</div>
        <div className="mt-1 text-lg font-semibold text-white">
          {feasibilityStatusLabel(data.feasibility.status)}
        </div>
        <p className="mt-1 text-sm text-gray-400">
          {data.feasibility.confidence_reason} (Konfidenz: {data.feasibility.confidence_level})
        </p>
        {data.feasibility.conditions.length > 0 ? (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-100">
            {data.feasibility.conditions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="grid gap-3 text-sm md:grid-cols-2">
        <div className="rounded-lg bg-gray-900 p-3">
          <div className="text-xs text-gray-400">Spannungsfall (Formel)</div>
          <div className="mt-1 font-mono text-white">
            {fmt(data.voltage_drop_analysis.delta_u_percent, 2)} % (Grenze{" "}
            {fmt(data.voltage_drop_analysis.limit_percent, 1)} %)
          </div>
          <p className="mt-1 text-xs text-gray-500">{data.voltage_drop_analysis.formula}</p>
        </div>
        <div className="rounded-lg bg-gray-900 p-3">
          <div className="text-xs text-gray-400">Kurzschluss</div>
          <div className="mt-1 text-white">
            {data.short_circuit_analysis.cannot_calculate
              ? "Nicht berechenbar (Netzdaten fehlen)"
              : `${fmt(data.short_circuit_analysis.ik_max_ka ?? 0, 2)} kA (vereinfacht)`}
          </div>
          <p className="mt-1 text-xs text-gray-500">{data.short_circuit_analysis.disclaimer}</p>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-blue-200">
          N-1-Bewertung (keine Vollanalyse)
        </div>
        <p className="mt-1 text-sm text-gray-300">{data.n1_assessment.recommendation}</p>
        <p className="mt-2 text-xs text-gray-500">{data.n1_assessment.disclaimer}</p>
      </div>

      {data.assumptions.length > 0 ? (
        <div className="mt-4">
          <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Dokumentierte Annahmen</div>
          <ul className="mt-2 space-y-2">
            {data.assumptions.map((a) => (
              <li
                key={`${a.parameter}-${a.assumed_value}`}
                className="rounded-lg border border-white/5 bg-black/20 px-3 py-2 text-sm text-gray-300"
              >
                <span className="font-medium text-white">{a.parameter}:</span> {a.assumed_value} — {a.reason}
                <span className="ml-2 text-xs text-gray-500">({a.confidence})</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
