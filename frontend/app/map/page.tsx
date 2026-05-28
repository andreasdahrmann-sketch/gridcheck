"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowRight, MapPinned } from "lucide-react";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { listProjects, type Project } from "@/lib/api/projects";
import { hasMapboxToken } from "@/lib/mapbox/config";
import type { ProjectMapMarker } from "@/components/map/ProjectsLeafletMap";

const ProjectsLeafletMap = dynamic(() => import("@/components/map/ProjectsLeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[440px] items-center justify-center rounded-[24px] border border-white/10 bg-black/20 text-sm text-text-muted">
      Lade Karte...
    </div>
  ),
});

function extractMarker(project: Project): ProjectMapMarker | null {
  const location = (project.role_inputs?.project_location ?? null) as
    | { latitude?: number | null; longitude?: number | null }
    | null;
  const lat = Number(location?.latitude);
  const lng = Number(location?.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  if (lat === 0 && lng === 0) return null;
  return {
    id: project.id,
    name: project.name,
    plz: project.plz,
    typ: project.typ,
    leistung_kw: project.leistung_kw,
    latitude: lat,
    longitude: lng,
  };
}

export default function MapPage() {
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const projects = projectsQuery.data ?? [];
  const markers = useMemo(
    () => projects.map(extractMarker).filter((m): m is ProjectMapMarker => m !== null),
    [projects],
  );
  const missingLocationCount = projects.length - markers.length;
  const mapboxReady = hasMapboxToken();

  return (
    <>
      <section className="border-b border-border/70 pb-6">
        <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-cyan">Karte</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Standort- & Netzkontext</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
          Uebersicht Ihrer Projekte mit Kartenbezug. Marker zeigen Projekte mit erfasstem Standort; detaillierte
          Netzplan-Karten erscheinen pro Analyse im Projekt-Workspace.
        </p>
        {!mapboxReady ? (
          <p className="mt-3 text-xs text-amber-200">
            Hinweis: NEXT_PUBLIC_MAPBOX_TOKEN fehlt. Karte verwendet OSM-Tiles als Fallback.
          </p>
        ) : null}
      </section>

      <section className="mt-8 space-y-4">
        <div className="rounded-[24px] border border-white/10 bg-white/5 p-2 sm:p-3">
          {projectsQuery.isLoading ? (
            <div className="flex h-[440px] items-center justify-center text-sm text-text-muted">
              Lade Projekte...
            </div>
          ) : markers.length === 0 ? (
            <div className="flex h-[440px] flex-col items-center justify-center gap-2 text-center text-sm text-text-muted">
              <MapPinned className="h-6 w-6 text-brand-cyan" aria-hidden />
              <p>Noch keine Projekte mit Standortkoordinaten erfasst.</p>
              <p className="max-w-md text-xs text-text-dim">
                Erfassen Sie eine Adresse im Projekt-Setup, damit die Lage hier sichtbar wird.
              </p>
              <Link
                href="/projects"
                className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand-cyan hover:underline"
              >
                Projekte oeffnen
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          ) : (
            <ProjectsLeafletMap markers={markers} />
          )}
        </div>

        {missingLocationCount > 0 ? (
          <p className="text-xs text-text-dim">
            {missingLocationCount} Projekt{missingLocationCount === 1 ? "" : "e"} ohne Standortkoordinaten – per
            Adresssuche im Projekt-Setup ergaenzbar.
          </p>
        ) : null}
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-2">
        <div className="rounded-[24px] border border-white/10 bg-white/5 p-6">
          <div className="flex items-center gap-2 text-brand-cyan">
            <MapPinned className="h-5 w-5" aria-hidden />
            <h2 className="text-lg font-semibold text-white">Projektliste</h2>
          </div>
          {projectsQuery.isLoading ? (
            <p className="mt-4 text-sm text-text-muted">Lade Projekte…</p>
          ) : projects.length === 0 ? (
            <p className="mt-4 text-sm text-text-muted">
              Noch keine Projekte. Legen Sie ein Projekt an oder starten Sie einen Check mit Adresssuche.
            </p>
          ) : (
            <ul className="mt-4 space-y-2">
              {projects.slice(0, 12).map((project) => {
                const marker = extractMarker(project);
                return (
                  <li key={project.id}>
                    <Link
                      href={`/projects/${project.id}`}
                      className="flex items-center justify-between rounded-xl border border-white/10 bg-black/10 px-4 py-3 text-sm transition hover:border-brand-cyan/30"
                    >
                      <span className="font-medium text-white">{project.name}</span>
                      <span className="text-text-dim">
                        PLZ {project.plz}
                        {marker ? "" : " · ohne Standort"}
                      </span>
                    </Link>
                  </li>
                );
              })}
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
            Vor-Ort-Marker dokumentieren Trafos, Umspannwerke und Schaltstationen mit GPS und Fotos. Netzplan-Karten
            erscheinen pro Analyse im Projekt-Detail.
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
