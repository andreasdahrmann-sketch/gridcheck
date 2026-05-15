"use client";

import { Fragment, useEffect, useMemo } from "react";
import L, { divIcon, latLngBounds } from "leaflet";
import {
  Circle,
  MapContainer,
  Marker,
  Polyline,
  TileLayer,
  Tooltip,
  ZoomControl,
  useMap,
} from "react-leaflet";
import { getMapboxTileUrl } from "@/lib/mapbox/config";
import type {
  NetzplanMapNode,
  NetzplanMapScene,
  NetzplanProjectLocation,
  NetzplanTone,
} from "@/lib/netzplan/map-scene";

const TONE_COLORS: Record<
  NetzplanTone,
  {
    line: string;
    fill: string;
    halo: string;
    text: string;
  }
> = {
  good: {
    line: "#34d399",
    fill: "#052e26",
    halo: "rgba(52,211,153,0.18)",
    text: "#d1fae5",
  },
  warn: {
    line: "#f59e0b",
    fill: "#3a2503",
    halo: "rgba(245,158,11,0.2)",
    text: "#fde68a",
  },
  critical: {
    line: "#fb7185",
    fill: "#3b0f18",
    halo: "rgba(251,113,133,0.22)",
    text: "#ffe4e6",
  },
  neutral: {
    line: "#38bdf8",
    fill: "#082f49",
    halo: "rgba(56,189,248,0.18)",
    text: "#e0f2fe",
  },
};

const MARKER_LABELS: Record<NetzplanMapNode["kind"], string> = {
  nap: "NAP",
  station: "STA",
  nvp: "NVP",
  support: "AUX",
  bottleneck: "ENG",
};

function FitSceneBounds({ scene }: { scene: NetzplanMapScene }) {
  const map = useMap();

  useEffect(() => {
    const bounds = latLngBounds(
      [
        [scene.projectLocation.position.lat, scene.projectLocation.position.lng] as [number, number],
        ...scene.nodes.map((node) => [node.position.lat, node.position.lng] as [number, number]),
      ],
    );
    bounds.extend([scene.center.lat, scene.center.lng]);
    if (scene.projectLocation.areaRadiusM > 0) {
      const delta = scene.projectLocation.areaRadiusM / 111_320;
      bounds.extend([
        scene.projectLocation.position.lat + delta,
        scene.projectLocation.position.lng + delta,
      ]);
      bounds.extend([
        scene.projectLocation.position.lat - delta,
        scene.projectLocation.position.lng - delta,
      ]);
    }
    map.fitBounds(bounds.pad(0.22), { maxZoom: 12 });
  }, [map, scene]);

  return null;
}

function buildMarkerIcon(node: NetzplanMapNode): L.DivIcon {
  const palette = TONE_COLORS[node.tone];
  const label = MARKER_LABELS[node.kind];
  const size = node.kind === "bottleneck" ? 48 : 42;

  return divIcon({
    className: "",
    html: `
      <div style="
        display:flex;
        align-items:center;
        justify-content:center;
        width:${size}px;
        height:${size}px;
        border-radius:999px;
        border:2px solid ${palette.line};
        background:${palette.fill};
        color:${palette.text};
        font:700 11px/1 Inter, system-ui, sans-serif;
        letter-spacing:0.08em;
        box-shadow:0 0 0 8px ${palette.halo};
      ">
        ${label}
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function projectSourceLabel(source: NetzplanProjectLocation["source"]): string {
  switch (source) {
    case "coordinates":
      return "GPS";
    case "address":
      return "ADR";
    case "ort":
      return "ORT";
    case "plz":
      return "PLZ";
  }
}

function buildProjectIcon(projectLocation: NetzplanProjectLocation): L.DivIcon {
  const label = projectSourceLabel(projectLocation.source);
  return divIcon({
    className: "",
    html: `
      <div style="
        display:flex;
        align-items:center;
        justify-content:center;
        width:52px;
        height:52px;
        border-radius:18px;
        border:2px solid #f97316;
        background:#2a1304;
        color:#fff7ed;
        font:700 11px/1 Inter, system-ui, sans-serif;
        letter-spacing:0.08em;
        box-shadow:0 0 0 10px rgba(249,115,22,0.18);
      ">
        ${label}
      </div>
    `,
    iconSize: [52, 52],
    iconAnchor: [26, 26],
  });
}

export default function NetzplanLeafletMap({ scene }: { scene: NetzplanMapScene }) {
  const tileUrl = getMapboxTileUrl();
  const markerIcons = useMemo(() => {
    const next = new Map<string, L.DivIcon>();
    scene.nodes.forEach((node) => {
      next.set(node.id, buildMarkerIcon(node));
    });
    return next;
  }, [scene.nodes]);
  const projectIcon = useMemo(() => buildProjectIcon(scene.projectLocation), [scene.projectLocation]);

  if (!tileUrl) {
    return null;
  }

  return (
    <MapContainer
      center={[scene.center.lat, scene.center.lng]}
      zoom={10}
      zoomControl={false}
      scrollWheelZoom={false}
      className="h-full min-h-[420px] w-full rounded-[24px]"
    >
      <ZoomControl position="bottomright" />
      <FitSceneBounds scene={scene} />

      <TileLayer
        attribution='&copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url={tileUrl}
        tileSize={512}
        zoomOffset={-1}
      />

      {scene.projectLocation.areaRadiusM > 0 && (
        <Circle
          center={[scene.projectLocation.position.lat, scene.projectLocation.position.lng]}
          radius={scene.projectLocation.areaRadiusM}
          pathOptions={{
            color: "#f97316",
            fillColor: "#f97316",
            fillOpacity: 0.08,
            dashArray: scene.projectLocation.approximate ? "8 12" : undefined,
            weight: 2,
          }}
        >
          <Tooltip sticky>
            <div className="space-y-1">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
                Standortfenster
              </div>
              <div className="text-sm text-white">
                {scene.projectLocation.approximate
                  ? `Ungefaehre Lage mit ca. ${Math.round(scene.projectLocation.areaRadiusM)} m Suchradius.`
                  : `Optionaler Flaechenrahmen mit ca. ${Math.round(scene.projectLocation.areaRadiusM)} m Radius.`}
              </div>
            </div>
          </Tooltip>
        </Circle>
      )}

      <Marker
        position={[scene.projectLocation.position.lat, scene.projectLocation.position.lng]}
        icon={projectIcon}
      >
        <Tooltip direction="top" offset={[0, -20]}>
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
              Echter Projektstandort
            </div>
            <div className="text-sm text-white">{scene.projectLocation.label}</div>
            <div className="text-xs text-slate-300">{scene.projectLocation.resolvedLabel}</div>
            <div className="text-[11px] text-slate-400">{scene.projectLocation.detail}</div>
          </div>
        </Tooltip>
      </Marker>

      {scene.segments.map((segment) => {
        const palette = TONE_COLORS[segment.tone];
        const positions = segment.points.map((point) => [point.lat, point.lng] as [number, number]);

        return (
          <Fragment key={segment.id}>
            <Polyline
              positions={positions}
              pathOptions={{
                color: palette.line,
                opacity: 0.18,
                weight: (segment.weight ?? 7) + 10,
              }}
            />
            <Polyline
              positions={positions}
              pathOptions={{
                color: palette.line,
                opacity: 0.92,
                weight: segment.weight ?? 7,
                dashArray: segment.dashed ? "14 12" : undefined,
              }}
            >
              <Tooltip sticky>
                <div className="space-y-1">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
                    {segment.label}
                  </div>
                  <div className="text-sm text-white">{segment.detail}</div>
                  <div className="text-[11px] text-slate-400">
                    {segment.approximate ? "Heuristischer Netzpfad" : "Georeferenzierter Pfad"}
                  </div>
                </div>
              </Tooltip>
            </Polyline>
          </Fragment>
        );
      })}

      {scene.nodes.map((node) => (
        <Marker
          key={node.id}
          position={[node.position.lat, node.position.lng]}
          icon={markerIcons.get(node.id)!}
        >
          <Tooltip direction="top" offset={[0, -18]}>
            <div className="space-y-1">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
                {node.label}
              </div>
              <div className="text-sm text-white">{node.detail}</div>
              <div className="text-[11px] text-slate-400">
                {node.approximate ? "Position heuristisch abgeleitet" : "PLZ-geocodierte Position"}
              </div>
            </div>
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
