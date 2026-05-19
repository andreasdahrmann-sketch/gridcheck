"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";

const STEPS = [
  { id: "validate", label: "Eingaben pruefen" },
  { id: "engine", label: "Netzdiagnose berechnen" },
  { id: "persist", label: "Ergebnis speichern" },
] as const;

type Props = {
  active?: boolean;
  className?: string;
};

export default function AnalysisProgressPanel({ active = true, className = "" }: Props) {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      setStepIndex(0);
      return;
    }

    setStepIndex(0);
    const timers = [
      window.setTimeout(() => setStepIndex(1), 1200),
      window.setTimeout(() => setStepIndex(2), 4500),
    ];

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [active]);

  if (!active) return null;

  const progressValue = ((stepIndex + 1) / STEPS.length) * 100;

  return (
    <div
      className={`rounded-2xl border border-brand-cyan/25 bg-brand-cyan/5 px-4 py-4 ${className}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 shrink-0 animate-spin text-brand-cyan" aria-hidden />
        <div>
          <p className="text-sm font-semibold text-white">Analyse laeuft</p>
          <p className="mt-0.5 text-xs text-text-muted">
            {STEPS[stepIndex]?.label ?? "Bitte warten…"} – typisch 10–30 Sekunden.
          </p>
        </div>
      </div>

      <Progress value={progressValue} className="mt-4 h-2 bg-white/10" />

      <ol className="mt-4 grid gap-2 sm:grid-cols-3">
        {STEPS.map((step, index) => {
          const done = index < stepIndex;
          const current = index === stepIndex;
          return (
            <li
              key={step.id}
              className={`rounded-xl border px-3 py-2 text-xs ${
                current
                  ? "border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan"
                  : done
                    ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                    : "border-white/10 bg-black/10 text-text-dim"
              }`}
            >
              {step.label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
