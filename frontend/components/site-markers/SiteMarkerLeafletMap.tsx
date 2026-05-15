"use client";

import { useMemo } from "react";
import { Circle, MapContainer, Marker, TileLayer, Tooltip } from "react-leaflet";
import { divIcon, latLngBounds } from "leaflet";
import type { SiteMarker } from "@/lib/api/site-markers";
import { getMapboxTileUrl } from "@/lib/mapbox/config";

type DraftPosition = {
  latitude: number;
  longitude: number;
  accuracyM?: number | null;
};

type SiteMarkerLeafletMapProps = {
  draftPosition: DraftPosition | null;
  markers: SiteMarker[];
};

function buildPillIcon(label: string, tone: "draft" | "saved") {
  const palette =
    tone === "draft"
      ? {
          border: "#EE7F2D",
          background: "#2A1304",
          text: "#FFF7ED",
          halo: "rgba(238,127,45,0.18)",
        }
      : {
          border: "#5FD0B8",
          background: "#0A2323",
          text: "#E7F3F0",
          halo: "rgba(95,208,184,0.16)",
        };

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
        border:2px solid ${palette.border};
        background:${palette.background};
        color:${palette.text};
        font:700 11px/1 Inter, system-ui, sans-serif;
        letter-spacing:0.08em;
        box-shadow:0 0 0 10px ${palette.halo};
      ">
        ${label}
      </div>
    `,
    iconSize: [44, 44],
    iconAnchor: [22, 22],
  });
}

function assetShortLabel(assetType: SiteMarker["asset_type"]) {
  switch (assetType) {
    case "ortsnetztrafo":
      return "ONT";
    case "umspannwerk":
      return "UW";
    case "schaltstation":
      return "SS";
  }
}

export default function SiteMarkerLeafletMap({ draftPosition, markers }: SiteMarkerLeafletMapProps) {
  const tileUrl = getMapboxTileUrl() ?? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  const usingMapbox = tileUrl.includes("mapbox.com");

  const bounds = useMemo(() => {
    const positions: [number, number][] = [];

    if (draftPosition) {
      positions.push([draftPosition.latitude, draftPosition.longitude]);
      if (draftPosition.accuracyM && draftPosition.accuracyM > 10) {
        const delta = draftPosition.accuracyM / 111_320;
        positions.push([draftPosition.latitude + delta, draftPosition.longitude + delta]);
        positions.push([draftPosition.latitude - delta, draftPosition.longitude - delta]);
      }
    }

    markers.forEach((marker) => {
      positions.push([marker.latitude, marker.longitude]);
    });

    if (positions.length === 0) {
      positions.push([51.1657, 10.4515]);
    }

    return latLngBounds(positions).pad(0.22);
  }, [draftPosition, markers]);

  return (
    <MapContainer
      bounds={bounds}
      scrollWheelZoom={false}
      zoomControl={false}
      className="h-[320px] w-full rounded-[24px] sm:h-[360px]"
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

      {draftPosition ? (
        <>
          {draftPosition.accuracyM ? (
            <Circle
              center={[draftPosition.latitude, draftPosition.longitude]}
              radius={draftPosition.accuracyM}
              pathOptions={{
                color: "#EE7F2D",
                fillColor: "#EE7F2D",
                fillOpacity: 0.08,
                weight: 2,
              }}
            />
          ) : null}
          <Marker
            position={[draftPosition.latitude, draftPosition.longitude]}
            icon={buildPillIcon("NEU", "draft")}
          >
            <Tooltip direction="top" offset={[0, -16]}>
              Aktuelle Erfassungsposition
            </Tooltip>
          </Marker>
        </>
      ) : null}

      {markers.map((marker) => (
        <Marker
          key={marker.id}
          position={[marker.latitude, marker.longitude]}
          icon={buildPillIcon(assetShortLabel(marker.asset_type), "saved")}
        >
          <Tooltip direction="top" offset={[0, -16]}>
            {marker.asset_type} #{marker.id}
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
