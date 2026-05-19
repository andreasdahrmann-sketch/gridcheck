"use client";

import Link from "next/link";
import { ArrowRight, MapPinned } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { listProjects } from "@/lib/api/projects";

export default function MapPage() {
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const projects = projectsQuery.data ?? [];

  return (
    <>
      <section className="border-b border-border/70 pb-6">
        <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-cyan">Karte</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Standort- & Netzkontext</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
          Uebersicht Ihrer Projekte mit Kartenbezug. Detaillierte Netzplan-Karten erscheinen nach einer Analyse im
          Projekt-Workspace; Vor-Ort-Marker erfassen Indizien im Feld.
        </p>
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-2">
        <div className="rounded-[24px] border border-white/10 bg-white/5 p-6">
          <div className="flex items-center gap-2 text-brand-cyan">
            <MapPinned className="h-5 w-5" aria-hidden />
            <h2 className="text-lg font-semibold text-white">Projektstandorte</h2>
          </div>
          {projectsQuery.isLoading ? (
            <p className="mt-4 text-sm text-text-muted">Lade Projekte…</p>
          ) : projects.length === 0 ? (
            <p className="mt-4 text-sm text-text-muted">
              Noch keine Projekte. Legen Sie ein Projekt an oder starten Sie einen Check mit Adresssuche.
            </p>
          ) : (
            <ul className="mt-4 space-y-2">
              {projects.slice(0, 12).map((project) => (
                <li key={project.id}>
                  <Link
                    href={`/projects/${project.id}`}
                    className="flex items-center justify-between rounded-xl border border-white/10 bg-black/10 px-4 py-3 text-sm transition hover:border-brand-cyan/30"
                  >
                    <span className="font-medium text-white">{project.name}</span>
                    <span className="text-text-dim">PLZ {project.plz}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link
            href="/projects"
            className="mt-4 inline-flex items-center text-sm font-semibold text-brand-cyan hover:underline"
          >
            Alle Projekte
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </div>

        <div className="rounded-[24px] border border-dashed border-white/15 bg-black/10 p-6">
          <h2 className="text-lg font-semibold text-white">Vor-Ort & Netzplan</h2>
          <p className="mt-3 text-sm leading-6 text-text-muted">
            Mapbox-Kartenausschnitte und OSM-Hinweise werden pro Analyse im Ergebnis und Projekt-Detail angezeigt. Der
            Marker-Flow dokumentiert GPS und Fotos vor Ort.
          </p>
          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <Link
              href="/site-markers"
              className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/5"
            >
              Vor-Ort-Marker
            </Link>
            <Link
              href="/projektierer"
              className="inline-flex items-center justify-center rounded-xl bg-brand-orange px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-orangeHover"
            >
              Analyse starten
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
