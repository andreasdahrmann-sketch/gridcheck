"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createProject, deleteProject, listProjects } from "@/lib/api/projects";
import { getProjectCommercialInsight, summarizeProjectPortfolio } from "@/lib/project-commercial";
import type { Project } from "@/lib/api/projects";
import { readUserPreferences } from "@/lib/user-preferences";

const PROJECT_TYPE_OPTIONS = [
  { value: "pv", label: "PV" },
  { value: "wind", label: "Wind" },
  { value: "bess", label: "BESS" },
  { value: "ladepark", label: "Ladepark" },
  { value: "sonstiges", label: "Sonstiges" },
];

const cardClass = "rounded-[24px] border border-border/70 bg-bg-card/80 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";

export default function ProjectsPage() {
  const [name, setName] = useState("");
  const [plz, setPlz] = useState("");
  const [typ, setTyp] = useState("pv");
  const [leistungKw, setLeistungKw] = useState("1000");
  const [uiMessage, setUiMessage] = useState<string | null>(null);
  const [compactCards, setCompactCards] = useState(false);
  const [deletingProjectId, setDeletingProjectId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const projectsQuery = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  useEffect(() => {
    setCompactCards(readUserPreferences().compactProjectCards);
  }, []);

  const createMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      setName("");
      setPlz("");
      setUiMessage("Projekt erstellt.");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      setUiMessage("Projekt geloescht.");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const portfolioSummary = summarizeProjectPortfolio(projectsQuery.data ?? []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    await createMutation.mutateAsync({
      name,
      plz,
      typ,
      leistung_kw: Number(leistungKw),
      role_inputs: {
        plz,
        antragsteller: name,
        anlagentyp:
          typ === "pv" ? "solar" :
          typ === "wind" ? "wind" :
          typ === "bess" || typ === "battery" ? "batterie" :
          typ === "ladepark" ? "ladepark" :
          "sonstiges",
        anschlussleistung_kw: Number(leistungKw),
      },
    });
  }

  async function onDelete(projectId: number) {
    setDeletingProjectId(projectId);
    try {
      await deleteMutation.mutateAsync(projectId);
    } finally {
      setDeletingProjectId(null);
    }
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <section className="flex flex-col gap-3 border-b border-border/70 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-cyan">Portfolio</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Projekte</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
              Projekte anlegen, priorisieren und fachlich sauber in Basis-, Premium-, Pro- oder Servicepfade ueberfuehren.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-text-muted">
            {compactCards ? "Kompakte Kartenansicht aktiv" : "Komfortable Kartenansicht aktiv"}
          </div>
        </section>

        <section className="mt-6 grid gap-3 md:grid-cols-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Noch ohne Run</p>
            <p className="mt-2 text-2xl font-semibold text-white">{portfolioSummary.unchecked}</p>
            <p className="mt-1 text-xs leading-5 text-text-muted">Hier fehlt noch der erste kontobezogene Paketkontext.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Basis-Scope</p>
            <p className="mt-2 text-2xl font-semibold text-white">{portfolioSummary.basis}</p>
            <p className="mt-1 text-xs leading-5 text-text-muted">Diese Projekte laufen noch im kompakten Screening-Pfad.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Entscheidungsbedarf</p>
            <p className="mt-2 text-2xl font-semibold text-white">{portfolioSummary.needsDecision}</p>
            <p className="mt-1 text-xs leading-5 text-text-muted">Hier sollte die Paket- oder Serviceentscheidung aktiv getroffen werden.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Betreute Nachlaeufe</p>
            <p className="mt-2 text-2xl font-semibold text-white">{portfolioSummary.serviceFollowups}</p>
            <p className="mt-1 text-xs leading-5 text-text-muted">Professional-/Servicefaelle mit sichtbarem Nachlauf.</p>
          </div>
        </section>

        <section className="mt-6 rounded-[24px] border border-white/10 bg-black/10 px-5 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-white">Portfolio-Fokus fuer kaufbare Entscheidungen</p>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">
                Nicht jedes Projekt braucht sofort Professional. Die Portfolioansicht trennt bewusst zwischen erstem
                Screening, vertieftem Self-Serve, laufendem Pro-Pfad und betreutem Servicefall.
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Link
                href="/settings"
                className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
              >
                Tarife & History
              </Link>
              <Link
                href="/contact?intent=upgrade"
                className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
              >
                Paketwahl abstimmen
              </Link>
            </div>
          </div>
        </section>

        {uiMessage ? (
          <div className="mt-6 rounded-2xl border border-brand-cyan/30 bg-brand-cyan/10 px-4 py-3 text-sm text-brand-cyan">
            {uiMessage}
          </div>
        ) : null}

        <section className="mt-6">
          <Card className={cardClass}>
            <CardHeader>
              <CardTitle className="text-white">Neues Projekt</CardTitle>
              <CardDescription className="text-text-muted">
                Legt einen belastbaren Projekteinstieg fuer Analyse, Dashboard und Freigaben an.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={onCreate} className="grid gap-3 lg:grid-cols-[minmax(0,1.5fr)_120px_160px_150px_auto]">
                <Input
                  className={fieldClass}
                  placeholder="Projektname"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
                <Input
                  className={fieldClass}
                  placeholder="PLZ"
                  value={plz}
                  onChange={(e) => setPlz(e.target.value)}
                  required
                  maxLength={5}
                  inputMode="numeric"
                />
                <select
                  className="h-11 rounded-xl border border-border/70 bg-white/5 px-3 text-sm text-white outline-none transition focus:border-brand-cyan/70"
                  value={typ}
                  onChange={(e) => setTyp(e.target.value)}
                  required
                >
                  {PROJECT_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value} className="bg-bg text-white">
                      {option.label}
                    </option>
                  ))}
                </select>
                <Input
                  className={fieldClass}
                  placeholder="Leistung kW"
                  value={leistungKw}
                  onChange={(e) => setLeistungKw(e.target.value)}
                  required
                  inputMode="decimal"
                />
                <Button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="h-11 rounded-xl bg-brand-orange px-5 text-white hover:bg-brand-orangeHover"
                >
                  {createMutation.isPending ? "Erstellt..." : "Projekt erstellen"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </section>

        <section className="mt-6 space-y-3">
          {projectsQuery.isLoading ? (
            <div className="rounded-2xl border border-border bg-bg-elev px-4 py-4 text-sm text-text-muted">
              Lade Projekte...
            </div>
          ) : null}
          {projectsQuery.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-4 text-sm text-red-300">
              Projekte konnten nicht geladen werden. Bitte erneut einloggen.
            </div>
          ) : null}
          {(projectsQuery.data ?? []).map((project) => {
            const resultScore =
              typeof project.role_results?.score === "number" ? `${project.role_results.score}/100` : "Noch kein Check";
            const n1Label =
              typeof project.role_results?.n1?.n1_klasse === "string"
                ? project.role_results.n1.n1_klasse
                : typeof (project.role_results as { n1_klasse?: unknown })?.n1_klasse === "string"
                  ? ((project.role_results as { n1_klasse?: string }).n1_klasse ?? null)
                  : null;
            const hasExtendedProfile = Boolean(project.role_inputs?.project_components?.length);
            const insight = getProjectCommercialInsight(project);
            const stageToneClass =
              insight.stageTone === "warning"
                ? "border-amber-300/20 bg-amber-300/10 text-amber-100"
                : insight.stageTone === "info"
                  ? "border-brand-cyan/20 bg-brand-cyan/10 text-brand-cyan"
                  : insight.stageTone === "success"
                    ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                    : "border-white/10 bg-black/20 text-white";

            return (
              <Card key={project.id} className={cardClass}>
                <CardContent className={compactCards ? "px-4 py-4" : "px-4 py-5 sm:px-5"}>
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="min-w-0 space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-medium text-brand-cyan">
                          #{project.id}
                        </span>
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white">
                          {project.typ.toUpperCase()}
                        </span>
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white">
                          {project.leistung_kw} kW
                        </span>
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white">
                          PLZ {project.plz}
                        </span>
                        <span className={`rounded-full border px-3 py-1 text-xs ${stageToneClass}`}>
                          {insight.stageLabel}
                        </span>
                      </div>

                      <div>
                        <p className="text-lg font-semibold text-white">{project.name}</p>
                        <p className="mt-1 text-sm text-text-muted">
                          Profil: {hasExtendedProfile ? "Erweitert" : "Basis"} | Ergebnis: {resultScore}
                          {n1Label ? ` | N-1: ${n1Label}` : ""}
                        </p>
                        <p className="mt-2 text-xs text-text-muted">
                          {insight.offerLabel} · {insight.scopeLabel} · {insight.reportLabel}
                        </p>
                        <p className="mt-2 text-sm leading-6 text-white/85">{insight.summary}</p>
                        <p className="mt-2 text-xs leading-5 text-text-dim">Naechster Schritt: {insight.nextStep}</p>
                        {project.updated_at ? (
                          <p className="mt-1 text-xs text-text-dim">
                            Zuletzt aktualisiert: {new Date(project.updated_at).toLocaleString("de-DE")}
                          </p>
                        ) : null}
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Link
                        href={insight.actionHref}
                        className="inline-flex h-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-medium text-white transition-colors hover:bg-white/10"
                      >
                        {insight.actionLabel}
                      </Link>
                      <Link
                        href={`/projects/${project.id}`}
                        className="inline-flex h-11 items-center justify-center rounded-xl border border-brand-cyan/30 bg-brand-cyan/10 px-4 text-sm font-medium text-brand-cyan transition-colors hover:bg-brand-cyan/15"
                      >
                        Projekt oeffnen
                      </Link>
                      <Button
                        type="button"
                        variant="outline"
                        disabled={deleteMutation.isPending && deletingProjectId === project.id}
                        onClick={() => onDelete(project.id)}
                        className="h-11 rounded-xl border-red-400/30 bg-red-500/10 px-4 text-red-300 hover:bg-red-500/15 hover:text-red-200"
                      >
                        {deleteMutation.isPending && deletingProjectId === project.id ? "Loescht..." : "Loeschen"}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}

          {(projectsQuery.data ?? []).length === 0 && !projectsQuery.isLoading ? (
            <div className="rounded-2xl border border-border bg-bg-elev px-4 py-8 text-center text-sm text-text-muted">
              Noch keine Projekte vorhanden. Legen Sie oben das erste Projekt an.
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
