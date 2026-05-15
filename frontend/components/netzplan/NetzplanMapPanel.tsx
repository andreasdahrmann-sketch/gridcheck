"use client";

import dynamic from "next/dynamic";
import { MapPinned, Network, Route, ShieldAlert, Zap } from "lucide-react";
import { useMemo } from "react";
import { usePlzLookup } from "@/lib/api/use-plz-lookup";
import { hasMapboxToken } from "@/lib/mapbox/config";
import { useProjectLocation } from "@/lib/mapbox/use-project-location";
import { buildNetzplanMapScene } from "@/lib/netzplan/map-scene";
import type { GridCheckInput, GridCheckResult } from "@/types";

const LeafletMap = dynamic(() => import("./NetzplanLeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="flex min-h-[420px] items-center justify-center rounded-[24px] border border-white/10 bg-black/20 text-sm text-text-muted">
      Lade Mapbox-Kartenausschnitt...
    </div>
  ),
});

interface NetzplanMapPanelProps {
  input: GridCheckInput;
  result: GridCheckResult;
  projectTitle: string;
  ortHint?: string;
}

function accuracyLabel(value: string): string {
  switch (value) {
    case "coordinates":
      return "Exakte Koordinate";
    case "postcode":
      return "PLZ-Zentrum";
    case "locality":
      return "Ort / Lokalitaet";
    case "place":
      return "Ort / Place";
    case "address":
      return "Adresse";
    case "region":
      return "Region";
    default:
      return "Unbekannt";
  }
}

function sourceDescription(source: string): string {
  switch (source) {
    case "coordinates":
      return "Explizit hinterlegte Koordinaten";
    case "address":
      return "Adress-/Standorthinweis mit Geocoding";
    case "ort":
      return "Ort + PLZ geocodiert";
    case "plz":
      return "Nur PLZ geocodiert";
    default:
      return "Unbekannte Quelle";
  }
}

export default function NetzplanMapPanel({
  input,
  result,
  projectTitle,
  ortHint,
}: NetzplanMapPanelProps) {
  const mapboxReady = hasMapboxToken();
  const locationStatus = useProjectLocation(input.plz, ortHint ?? input.ort, input.project_location);
  const plzLookupStatus = usePlzLookup(input.plz);

  const scene = useMemo(() => {
    if (locationStatus.kind !== "ok") return null;
    return buildNetzplanMapScene({
      input,
      result,
      projectTitle,
      projectLocation: locationStatus.data,
    });
  }, [input, locationStatus, projectTitle, result]);

  const vnbSummary =
    plzLookupStatus.kind === "ok"
      ? `${plzLookupStatus.data.vnb_kandidaten.length} VNB-Kandidaten, Confidence ${plzLookupStatus.data.confidence}`
      : plzLookupStatus.kind === "loading"
        ? "PLZ-Heuristik wird geladen..."
        : "PLZ-Heuristik noch nicht verfuegbar.";

  return (
    <div className="rounded-[26px] border border-border/60 bg-bg-card/70 p-4">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.22em] text-text-dim">Netzplan auf Mapbox-Basis</div>
          <div className="mt-1 text-sm text-text-muted">
            Echte Projektlage, soweit verfuegbar, kombiniert mit klar getrennten heuristischen Netzobjekten.
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="inline-flex items-center gap-2 rounded-full border border-brand-cyan/25 bg-brand-cyan/10 px-3 py-1 text-brand-cyan">
            <MapPinned className="h-3.5 w-3.5" />
            {mapboxReady ? "Mapbox aktiv" : "Mapbox Token fehlt"}
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-text-muted">
            <Route className="h-3.5 w-3.5 text-brand-orange" />
            Netzpfade heuristisch
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-text-muted">
            <Network className="h-3.5 w-3.5 text-brand-mint" />
            VNB-Lookup: {vnbSummary}
          </span>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_300px]">
        <div className="overflow-hidden rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(3,14,14,0.96)_0%,rgba(6,24,24,0.98)_100%)]">
          {!mapboxReady && (
            <div className="flex min-h-[420px] items-center justify-center p-6">
              <div className="max-w-md rounded-[22px] border border-amber-400/25 bg-amber-500/10 p-5 text-sm text-amber-100">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="mt-0.5 h-5 w-5 text-amber-300" />
                  <div>
                    <div className="font-semibold text-white">Mapbox ist vorbereitet, aber noch nicht aktiviert.</div>
                    <p className="mt-2 leading-6 text-amber-100/90">
                      Setze <code>NEXT_PUBLIC_MAPBOX_TOKEN</code>, damit der echte Kartenausschnitt und das
                      PLZ-Geocoding geladen werden koennen.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {mapboxReady && locationStatus.kind === "loading" && (
            <div className="flex min-h-[420px] items-center justify-center text-sm text-text-muted">
              Loese Projektstandort via Mapbox auf...
            </div>
          )}

          {mapboxReady && locationStatus.kind === "error" && (
            <div className="flex min-h-[420px] items-center justify-center p-6">
              <div className="max-w-md rounded-[22px] border border-rose-400/25 bg-rose-500/10 p-5 text-sm text-rose-100">
                <div className="font-semibold text-white">Kartenausschnitt konnte nicht geladen werden.</div>
                <p className="mt-2 leading-6">{locationStatus.message}</p>
              </div>
            </div>
          )}

          {mapboxReady && scene && <LeafletMap scene={scene} />}
        </div>

        <div className="space-y-4">
          <div className="rounded-[22px] border border-white/10 bg-white/5 p-4">
            <div className="flex items-center gap-2">
              <MapPinned className="h-4 w-4 text-brand-cyan" />
              <h4 className="text-sm font-semibold text-white">Kartenausschnitt</h4>
            </div>
            <div className="mt-3 space-y-3 text-sm text-text-muted">
              <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Standortquelle</div>
                <div className="mt-1 text-white">
                  {scene ? sourceDescription(scene.projectLocation.source) : "Wird nach erfolgreicher Aufloesung angezeigt"}
                </div>
                <div className="mt-1 text-xs text-text-muted">
                  {locationStatus.kind === "ok"
                    ? accuracyLabel(locationStatus.data.accuracy)
                    : "Koordinate vor Adresse vor Ort/PLZ"}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Standortlabel</div>
                <div className="mt-1 text-white">
                  {scene
                    ? scene.projectLocation.resolvedLabel
                    : input.project_location?.address_hint || ortHint || input.ort
                      ? `${input.project_location?.address_hint ?? ortHint ?? input.ort}`
                      : input.plz}
                </div>
                <div className="mt-1 text-xs text-text-muted">
                  {scene
                    ? scene.projectLocation.approximate
                      ? "Als ungefaehre Lage kenntlich gemacht."
                      : "Als echter Standortpunkt visualisiert."
                    : "Wird nach erfolgreicher Aufloesung angezeigt"}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Flaechenrahmen</div>
                <div className="mt-1 text-white">
                  {scene && scene.projectLocation.areaRadiusM > 0
                    ? `ca. ${Math.round(scene.projectLocation.areaRadiusM)} m Radius`
                    : "Kein separater Flaechenrahmen"}
                </div>
                <div className="mt-1 text-xs text-text-muted">
                  Optionaler Projekt- oder Unsicherheitsrahmen um den echten Standortmarker.
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Korridor</div>
                <div className="mt-1 text-white">
                  ca. {(input.entfernung_km || result.nvp_entfernung_km || 0).toFixed(1)} km
                </div>
                <div className="mt-1 text-xs text-text-muted">
                  Distanz aus Input/Backend; Netzpfade bleiben absichtlich indikativ.
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Engpassfokus</div>
                <div className="mt-1 text-white">
                  {Math.max(result.trafo_auslastung_pct, result.leitung_auslastung_pct).toFixed(1)} % Peak-Auslastung
                </div>
                <div className="mt-1 text-xs text-text-muted">
                  Hohe Auslastungen und Trassenrisiken werden farblich im Netzpfad hervorgehoben.
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-[22px] border border-white/10 bg-white/5 p-4">
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-brand-mint" />
              <h4 className="text-sm font-semibold text-white">Legende</h4>
            </div>
            <div className="mt-4 space-y-3 text-sm text-text-muted">
              {[
                {
                  label: "Echter Projektstandort",
                  description: "Orangefarbener Marker fuer Koordinate oder bestverfuegbare Geocoding-Lage.",
                  color: "bg-orange-400",
                },
                {
                  label: "Stationen / NAP / NVP",
                  description: "Knoten werden aus Distanz, Topologie und Backend-Metriken heuristisch entlang des Korridors platziert.",
                  color: "bg-emerald-400",
                },
                {
                  label: "Engpass / Risiko",
                  description: "Orange und Rot markieren Trafo-, Leitungs- oder Trassenstress im priorisierten Abschnitt.",
                  color: "bg-rose-400",
                },
              ].map((item) => (
                <div key={item.label} className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                  <div className="flex items-center gap-2 text-white">
                    <span className={`h-2.5 w-2.5 rounded-full ${item.color}`} />
                    <span className="font-medium">{item.label}</span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-text-muted">{item.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[22px] border border-brand-orange/20 bg-brand-orange/10 p-4">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-brand-orange" />
              <h4 className="text-sm font-semibold text-white">Transparenz</h4>
            </div>
            <ul className="mt-3 space-y-2 text-sm text-text-muted">
              <li className="flex gap-2">
                <span className="text-brand-orange">•</span>
                <span>Der Projektmarker zeigt die beste verfuegbare reale Lagequelle; NAP, Stationen und Leitungen bleiben heuristisch.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-brand-orange">•</span>
                <span>Wenn nur Ort oder PLZ bekannt sind, wird die Lage bewusst als ungefaehr mit Flaechenrahmen markiert.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-brand-orange">•</span>
                <span>VNB-Zuordnung kommt weiterhin aus dem bestehenden heuristischen PLZ-Lookup; die Farben zeigen keine verbindliche Kapazitaet.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
