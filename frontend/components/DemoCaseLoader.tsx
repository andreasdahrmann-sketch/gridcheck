"use client";

import { Battery, Sun, TriangleAlert } from "lucide-react";
import type { GridCheckInput } from "@/types";

export interface DemoCase {
  id: string;
  label: string;
  beschreibung: string;
  kundentyp: string;
  input: Partial<GridCheckInput>;
}

/** Sales-demo scenarios aligned with docs/RISIKO_STATUS.md MVP checklist. */
export const DEMO_CASES: DemoCase[] = [
  {
    id: "demo-pv-ms-auflagen",
    label: "[DEMO] PV 5 MW / MS – vorläufig C (Screening)",
    beschreibung:
      "Freiflächen-PV 5 MW am MS-Ring; Engine liefert vorläufig Entscheidung C mit N-1-Hinweisen, Empfehlungen und Auflagenkontext (Demo ohne NB-Daten).",
    kundentyp: "projektierer",
    input: {
      anlagentyp: "solar",
      anschlussleistung_kw: 5000,
      spannungsebene: "MS",
      plz: "04109",
      ort: "Leipzig",
      topologie: "ring",
      entfernung_km: 2,
      restkapazitaet_ms_mva: 10,
      sk_min_mva: 250,
      cos_phi: 0.95,
      richtung: "einspeisung",
      stakeholder_context: { customer_type: "projektierer" },
    },
  },
  {
    id: "demo-bess-grenzwertig",
    label: "[DEMO] BESS 10 MW / MS – vorläufig C (Trafo)",
    beschreibung:
      "Grosser Speicher mit hoher Trafoauslastung; Engine zeigt Trafo-Engpass und kritische N-1-Bewertung (Demo ohne verifizierte NB-Daten).",
    kundentyp: "speicherbetreiber",
    input: {
      anlagentyp: "batterie",
      anschlussleistung_kw: 10000,
      spannungsebene: "MS",
      plz: "30159",
      ort: "Hannover",
      topologie: "ring",
      entfernung_km: 3,
      restkapazitaet_ms_mva: 8,
      sk_min_mva: 250,
      richtung: "bidirektional",
      umspannwerk: {
        trafos: [
          { sn_mva: 10, belastung_aktuell_mw: 9 },
          { sn_mva: 10, belastung_aktuell_mw: 9 },
        ],
      },
      storage_profile: {
        has_storage: true,
        power_kw: 10000,
        energy_kwh: 20000,
      },
      stakeholder_context: { customer_type: "speicherbetreiber" },
    },
  },
  {
    id: "demo-nogo-thermik",
    label: "[DEMO] PV 250 kW / NS – vorläufig C (Thermik)",
    beschreibung:
      "Kurze NS-Leitung mit thermischem und Spannungs-Engpass; Engine liefert Entscheidung C (No-Go-Screening, keine NB-Zusage).",
    kundentyp: "projektierer",
    input: {
      anlagentyp: "solar",
      anschlussleistung_kw: 250,
      spannungsebene: "NS",
      plz: "44137",
      ort: "Dortmund",
      topologie: "stich",
      entfernung_km: 0.3,
      kabeltyp: "NAYY150",
      cos_phi: 0.95,
      richtung: "einspeisung",
      stakeholder_context: { customer_type: "projektierer" },
    },
  },
];

const DEMO_ICONS = [Sun, Battery, TriangleAlert] as const;

interface DemoCaseLoaderProps {
  onSelect: (demo: DemoCase) => void;
}

export default function DemoCaseLoader({ onSelect }: DemoCaseLoaderProps) {
  return (
    <div className="mb-6">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-yellow-400">
        Demo-Fälle – keine echten Netzdaten
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {DEMO_CASES.map((demo, index) => {
          const Icon = DEMO_ICONS[index] ?? Sun;
          return (
            <button
              key={demo.id}
              type="button"
              onClick={() => onSelect(demo)}
              className="rounded-lg border border-yellow-500/30 bg-gray-800 p-3 text-left transition-all hover:border-yellow-400 hover:bg-gray-700"
            >
              <div className="mb-2 flex items-center gap-2">
                <Icon className="h-4 w-4 text-yellow-400" aria-hidden />
                <p className="text-xs font-bold text-yellow-400">[DEMO]</p>
              </div>
              <p className="text-sm font-semibold text-white">{demo.label.replace("[DEMO] ", "")}</p>
              <p className="mt-1 text-xs text-gray-400">{demo.beschreibung}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function findDemoCaseById(id: string | null | undefined): DemoCase | undefined {
  if (!id) return undefined;
  return DEMO_CASES.find((demo) => demo.id === id);
}
