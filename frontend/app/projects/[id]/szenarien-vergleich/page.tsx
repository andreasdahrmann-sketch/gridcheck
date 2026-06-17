"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import ScenarioComparePanel from "@/components/projects/ScenarioComparePanel";
import { Header } from "@/components/Header";
import { getProject } from "@/lib/api/projects";
import type { GridCheckResult } from "@/types";

export default function ScenarioComparePage({ params }: { params: { id: string } }) {
  const projectId = params.id;

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(Number(projectId)),
    enabled: Number.isFinite(Number(projectId)),
  });

  const currentResult = (projectQuery.data?.role_results ?? null) as GridCheckResult | null;
  const projectIdNumber = Number(projectId);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Link
          href={`/projects/${projectId}`}
          className="mb-6 inline-flex items-center text-sm text-text-muted transition hover:text-white"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Zurueck zum Projekt
        </Link>
        <h1 className="text-3xl font-semibold text-white">Szenarienvergleich</h1>
        <p className="mt-2 max-w-3xl text-sm text-text-muted">
          Vorlaeufiger Vergleich zweier Analyse-Snapshots oder thermischer Szenarien. Ersetzt keine Netzbetreiber-Entscheidung.
        </p>
        <div className="mt-8">
          {!Number.isFinite(projectIdNumber) ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-200">
              Ungueltige Projekt-ID.
            </div>
          ) : projectQuery.isLoading ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-text-muted">
              Projektzugriff wird geprueft...
            </div>
          ) : projectQuery.isError || !projectQuery.data ? (
            <div className="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-5 text-sm text-amber-100">
              Szenarienvergleich nicht verfuegbar: Sie haben keinen Zugriff auf dieses Projekt oder es existiert nicht.
            </div>
          ) : (
            <ScenarioComparePanel projectId={projectId} currentResult={currentResult} />
          )}
        </div>
      </main>
    </div>
  );
}
