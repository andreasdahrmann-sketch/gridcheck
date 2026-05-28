"use client";

import { useMemo } from "react";
import Link from "next/link";
import { MapContainer, Marker, TileLayer, Tooltip, ZoomControl } from "react-leaflet";
import { divIcon, latLngBounds } from "leaflet";
import { getMapboxTileUrl } from "@/lib/mapbox/config";

export type ProjectMapMarker = {
  id: number;
  name: string;
  plz: string;
  typ?: string;
  leistung_kw?: number;
  latitude: number;
  longitude: number;
};

type Props = {
  markers: ProjectMapMarker[];
  height?: string;
};

const DEFAULT_CENTER: [number, number] = [51.1657, 10.4515];

function pillIcon(label: string) {
  return divIcon({
    className: "",
    html: `
      <div style="
        min-width:44px;
        height:44px;
        padding:0 12px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:999px;
        border:2px solid #5FD0B8;
        background:#0A2323;
        color:#E7F3F0;
        font:700 11px/1 Inter, system-ui, sans-serif;
        letter-spacing:0.06em;
        box-shadow:0 0 0 10px rgba(95,208,184,0.16);
      ">${label}</div>
    `,
    iconSize: [44, 44],
    iconAnchor: [22, 22],
  });
}

export default function ProjectsLeafletMap({ markers, height = "h-[440px]" }: Props) {
  const tileUrl = getMapboxTileUrl() ?? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  const usingMapbox = tileUrl.includes("mapbox.com");

  const bounds = useMemo(() => {
    if (markers.length === 0) return null;
    const positions = markers.map((m) => [m.latitude, m.longitude] as [number, number]);
    return latLngBounds(positions).pad(0.25);
  }, [markers]);

  return (
    <MapContainer
      bounds={bounds ?? undefined}
      center={bounds ? undefined : DEFAULT_CENTER}
      zoom={bounds ? undefined : 6}
      scrollWheelZoom
      zoomControl={false}
      className={`${height} w-full rounded-[24px]`}
    >
      <TileLayer
        attribution={
          usingMapbox
            ? '&copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }
        url={tileUrl}
        tileSize={usingMapbox ? 512 : 256}
        zoomOffset={usingMapbox ? -1 : 0}
      />
      <ZoomControl position="bottomright" />
      {markers.map((marker) => {
        const shortLabel = (marker.typ || "PRJ").toUpperCase().slice(0, 3);
        return (
          <Marker
            key={marker.id}
            position={[marker.latitude, marker.longitude]}
            icon={pillIcon(shortLabel)}
          >
            <Tooltip direction="top" offset={[0, -16]} permanent={false}>
              <div className="space-y-0.5">
                <div className="font-semibold text-sm">{marker.name}</div>
                <div className="text-xs">
                  PLZ {marker.plz}
                  {typeof marker.leistung_kw === "number" && marker.leistung_kw > 0
                    ? ` · ${Math.round(marker.leistung_kw)} kW`
                    : ""}
                </div>
                <Link href={`/projects/${marker.id}`} className="text-xs underline">
                  Projekt oeffnen
                </Link>
              </div>
            </Tooltip>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
