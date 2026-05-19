"use client";

import type { GridCalculationV2 } from "@/lib/schemas/grid-calculation";
import { feasibilityStatusLabel } from "@/lib/schemas/grid-calculation";
import { FEED_IN_CLASS_LABELS } from "@/lib/plant-types";

type Props = {
  data: GridCalculationV2;
  sectionClass: string;
  sectionTitle: string;
  fmt: (value: number, digits?: number) => string;
};

function ScreeningBlock({
  title,
  disclaimer,
  children,
}: {
  title: string;
  disclaimer?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-4 rounded-lg border border-white/10 bg-gray-900/60 p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-300">{title}</div>
      {children}
      {disclaimer ? <p className="mt-2 text-xs text-gray-500">{disclaimer}</p> : null}
    </div>
  );
}

export default function GridCalculationV2Panel({ data, sectionClass, sectionTitle, fmt }: Props) {
  const trafo = data.transformer_assessment;
  const protection = data.protection_concept_screening;
  const networkFb = data.network_feedback_screening;
  const coincidence = data.coincidence_factor_screening;
  const eeg = data.eeg_feed_in_screening;
  const reactive = data.reactive_power_screening;
  const persp = data.projektierer_perspective;

  return (
    <div className={sectionClass}>
      <h3 className={sectionTitle}>Strukturierte Vorpr?fung (Engine v{data.calculation_version})</h3>
      <p className="mb-3 text-xs text-gray-500">
        Differenzierte Plausibilit?tsbewertung mit dokumentierten Annahmen ? keine verbindliche
        Netzanschlusszusage, keine freie Trafo-Kapazit?t.
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

      <ScreeningBlock title="Transformator-Auslastung (ONT)" disclaimer={trafo.disclaimer}>
        {trafo.status === "insufficient_data" ? (
          <>
            <p className="mt-2 text-sm text-amber-100">Daten unzureichend ? keine Auslastung in % berechnet.</p>
            <p className="mt-1 text-xs text-gray-400">Erforderlich: {trafo.required_fields.join(", ")}</p>
            {trafo.missing_fields.length > 0 ? (
              <p className="mt-1 text-xs text-gray-500">Fehlend: {trafo.missing_fields.join("; ")}</p>
            ) : null}
          </>
        ) : (
          <>
            <p className="mt-2 text-sm text-gray-200">
              Screening: ca. {fmt(trafo.screened_total_utilization_percent ?? 0, 1)} % von{" "}
              {fmt(trafo.transformer_power_kva ?? 0, 0)} kVA (Bestand {fmt(trafo.existing_load_percent ?? 0, 1)} % + Projekt{" "}
              {fmt(trafo.project_apparent_kva ?? 0, 1)} kVA)
            </p>
            {trafo.screening_notes.map((n) => (
              <p key={n} className="mt-1 text-xs text-amber-100">
                {n}
              </p>
            ))}
          </>
        )}
      </ScreeningBlock>

      {protection.applicable ? (
        <ScreeningBlock title="Schutzkonzept (Einspeiseanlage)" disclaimer={protection.disclaimer}>
          <p className="mt-1 text-xs text-gray-400">Normbezug: {protection.voltage_level_ref}</p>
          <ul className="mt-2 space-y-2">
            {protection.checklist.map((item) => (
              <li key={item.topic} className="rounded border border-white/5 bg-black/20 px-3 py-2 text-sm">
                <span className="font-medium text-white">{item.topic}</span>
                <span className="ml-2 text-xs text-gray-500">({item.status})</span>
                <p className="mt-1 text-xs text-gray-400">{item.note}</p>
              </li>
            ))}
          </ul>
        </ScreeningBlock>
      ) : null}

      {networkFb.applicable ? (
        <ScreeningBlock title="Netzr?ckwirkungen" disclaimer={networkFb.disclaimer}>
          {networkFb.cannot_quantify ? (
            <p className="mt-2 text-xs text-amber-100">Ohne Messdaten nicht quantifizierbar ? VNB-Studie empfohlen.</p>
          ) : null}
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-300">
            {networkFb.topics.map((t) => (
              <li key={t.standard}>
                <span className="font-medium">{t.standard}</span> ({t.subject}): {t.warning}
              </li>
            ))}
          </ul>
        </ScreeningBlock>
      ) : null}

      <ScreeningBlock title="Gleichzeitigkeitsfaktor" disclaimer={coincidence.disclaimer}>
        <p className="mt-2 text-sm text-gray-300">
          Analyse nur f?r diesen Einzelanschluss
          {coincidence.single_connection_analysis ? " (kein Cluster-Modell)" : ""}.
        </p>
        {coincidence.warnings.map((w) => (
          <p key={w} className="mt-1 text-xs text-amber-100">
            {w}
          </p>
        ))}
      </ScreeningBlock>

      {eeg.applicable && (eeg.warnings.length > 0 || eeg.hints.length > 0 || eeg.feed_in_management_class) ? (
        <ScreeningBlock title="EEG 2023 / Einspeisemanagement" disclaimer={eeg.disclaimer}>
          {eeg.feed_in_management_class ? (
            <p className="mt-2 text-sm text-gray-200">
              Klasse: {FEED_IN_CLASS_LABELS[eeg.feed_in_management_class] ?? eeg.feed_in_management_class}
            </p>
          ) : null}
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-100">
            {eeg.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
            {eeg.hints.map((h) => (
              <li key={h} className="text-gray-300">
                {h}
              </li>
            ))}
          </ul>
        </ScreeningBlock>
      ) : null}

      {reactive.applicable ? (
        <ScreeningBlock title="Blindleistung / Q(U)" disclaimer={reactive.disclaimer}>
          <ul className="mt-2 space-y-2">
            {reactive.checklist.map((item) => (
              <li key={item.topic} className="rounded border border-white/5 bg-black/20 px-3 py-2 text-sm">
                <span className="font-medium text-white">{item.topic}</span>
                <p className="mt-1 text-xs text-gray-400">{item.note}</p>
              </li>
            ))}
          </ul>
        </ScreeningBlock>
      ) : null}

      {persp ? (
        <ScreeningBlock title="Projektierer: Anlage & Ablauf" disclaimer={persp.disclaimer}>
          <p className="mt-2 text-sm text-gray-200">
            {persp.plant_type_label} ? AC {fmt(persp.ac_kw, 0)} kW
            {persp.dc_kwp ? `, DC ${fmt(persp.dc_kwp, 0)} kWp` : ""}
            {persp.overbuild_ratio ? ` (DC/AC ? ${fmt(persp.overbuild_ratio, 2)})` : ""}
            , Screening {fmt(persp.screening_power_kw, 0)} kW, cos ? {fmt(persp.cos_phi, 2)}
          </p>
          <p className="mt-2 text-xs text-gray-400">
            Gleichzeitigkeit {fmt(persp.simultaneity_factor * 100, 0)} % ? nur Einzelprojekt (
            {typeof persp.kumulation_warning?.message === "string" ? persp.kumulation_warning.message : ""}
            )
          </p>
          <div className="mt-3 rounded border border-white/5 bg-black/20 p-3 text-sm">
            <div className="text-xs uppercase text-gray-400">Zeitplan (heuristisch)</div>
            <p className="mt-1 font-medium text-white">{persp.process_timeline.estimated_total}</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-gray-300">
              {persp.process_timeline.phases.map((ph) => (
                <li key={ph.phase}>
                  {ph.phase}: {ph.duration_weeks} ({ph.responsible})
                </li>
              ))}
            </ul>
          </div>
          <p className="mt-2 text-xs text-amber-100">{persp.bkz_hint.hint}</p>
          <p className="mt-1 text-xs text-gray-400">{persp.nvp_recommendation.nearest_node_hint}</p>
          <p className="mt-1 text-xs text-gray-500">{persp.nvp_recommendation.disclaimer}</p>
          {persp.tab_disclaimer.applicable ? (
            <p className="mt-2 text-xs text-blue-200">{persp.tab_disclaimer.message}</p>
          ) : null}
        </ScreeningBlock>
      ) : null}

      {data.norm_references_applied.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-lg border border-white/10">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-gray-900 text-xs uppercase text-gray-400">
              <tr>
                <th className="px-3 py-2">Norm</th>
                <th className="px-3 py-2">Titel</th>
                <th className="px-3 py-2">Anwendung</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-gray-300">
              {data.norm_references_applied.map((ref) => (
                <tr key={ref.code}>
                  <td className="px-3 py-2 font-mono text-white">{ref.code}</td>
                  <td className="px-3 py-2">{ref.title}</td>
                  <td className="px-3 py-2 text-xs">{ref.applied_to}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
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
                <span className="font-medium text-white">{a.parameter}:</span> {a.assumed_value} ? {a.reason}
                <span className="ml-2 text-xs text-gray-500">({a.confidence})</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
