"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import ScenarioComparePanel from "@/components/projects/ScenarioComparePanel";
import { STANDALONE_COMPARE_PROJECT_ID } from "@/lib/scenario-compare-snapshots";
import type { GridCheckResult } from "@/types";

const DRAFT_RESULT_KEY = "gridcheck:last-check-result";

export default function ProjektiererScenarioComparePage() {
  const [currentResult, setCurrentResult] = useState<GridCheckResult | null>(null);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(DRAFT_RESULT_KEY);
      if (raw) {
        setCurrentResult(JSON.parse(raw) as GridCheckResult);
      }
    } catch {
      setCurrentResult(null);
    }
  }, []);

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <div>
          <Link href="/projektierer" className="text-sm text-brand-cyan hover:underline">
            Zurueck zum Projektierer-Check
          </Link>
          <h1 className="mt-3 text-3xl font-semibold text-white">Szenarienvergleich</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">
            Vergleichen Sie zwei Analyse-Snapshots aus der aktuellen Browser-Session. Ersetzt keine Netzbetreiber-Entscheidung.
          </p>
        </div>
        <ScenarioComparePanel projectId={STANDALONE_COMPARE_PROJECT_ID} currentResult={currentResult} />
      </div>
    </main>
  );
}
