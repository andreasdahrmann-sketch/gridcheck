"use client";

import Link from "next/link";
import { ArrowRight, FileText } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { listAnalysisHistory, type AnalysisHistoryItem } from "@/lib/api/billing";
import { getRunStatusLabel } from "@/lib/product-decision-guide";

function statusBadgeClass(status: string) {
  if (status === "completed") return "border-emerald-400/20 bg-emerald-500/10 text-emerald-200";
  if (status === "failed" || status === "validation_failed" || status === "engine_failed") {
    return "border-red-500/30 bg-red-500/10 text-red-300";
  }
  return "border-amber-300/20 bg-amber-300/10 text-amber-100";
}

function ReportRow({ item }: { item: AnalysisHistoryItem }) {
  return (
    <li className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] ${statusBadgeClass(item.status)}`}>
          {getRunStatusLabel(item.status)}
        </span>
        <span className="text-xs text-text-dim">Run #{item.id}</span>
      </div>
      <p className="mt-2 text-sm font-medium text-white">
        {item.project_name ? (
          <Link href={`/projects/${item.project_id}`} className="hover:text-brand-cyan">
            {item.project_name}
          </Link>
        ) : (
          "Direktcheck"
        )}
      </p>
      <p className="mt-1 text-xs text-text-muted">
        {item.created_at ? new Date(item.created_at).toLocaleString("de-DE") : "—"}
        {item.score != null ? ` · Score ${item.score}/100` : ""}
      </p>
      {item.status === "completed" && item.project_id ? (
        <Link
          href={`/projects/${item.project_id}`}
          className="mt-2 inline-flex text-xs font-semibold text-brand-cyan hover:underline"
        >
          PDF im Projekt exportieren
        </Link>
      ) : null}
    </li>
  );
}

export default function ReportsPage() {
  const historyQuery = useQuery({
    queryKey: ["analysis-history", "reports"],
    queryFn: () => listAnalysisHistory(30),
  });

  const items = (historyQuery.data ?? []).filter((item) => item.status === "completed");

  return (
    <>
      <section className="border-b border-border/70 pb-6">
        <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-cyan">Reports</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Analyse-Reports</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
          Abgeschlossene Analysen mit exportierbarem Stakeholder-PDF. Fehlgeschlagene oder offene Runs finden Sie in der
          Analyse-History unter Einstellungen.
        </p>
      </section>

      <section className="mt-8">
        <div className="flex items-center gap-2 text-white">
          <FileText className="h-5 w-5 text-brand-cyan" aria-hidden />
          <h2 className="text-lg font-semibold">Abgeschlossene Runs</h2>
        </div>

        {historyQuery.isLoading ? (
          <p className="mt-4 text-sm text-text-muted">Lade Reports…</p>
        ) : items.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 px-6 py-8 text-center">
            <p className="text-sm text-text-muted">Noch keine abgeschlossenen Analysen mit Report-Export.</p>
            <Link
              href="/projektierer"
              className="mt-4 inline-flex items-center justify-center rounded-xl bg-brand-orange px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-orangeHover"
            >
              Erste Analyse starten
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        ) : (
          <ul className="mt-4 space-y-3">
            {items.map((item) => (
              <ReportRow key={item.id} item={item} />
            ))}
          </ul>
        )}

        <Link
          href="/settings"
          className="mt-6 inline-flex items-center text-sm font-semibold text-brand-cyan hover:underline"
        >
          Vollstaendige History & Tarife
          <ArrowRight className="ml-1 h-4 w-4" />
        </Link>
      </section>
    </>
  );
}
