"use client";

import { useEffect, useState } from "react";
import {
  GeoApiError,
  fetchOsmNearby,
  type OsmNearbyResponse,
} from "./geo";

export type OsmNearbyStatus =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; data: OsmNearbyResponse }
  | { kind: "error"; message: string };

const DEBOUNCE_MS = 400;
const cache = new Map<string, Promise<OsmNearbyResponse>>();

function makeCacheKey(lat: number, lon: number, radiusM: number, plz?: string): string {
  return `${lat.toFixed(5)}:${lon.toFixed(5)}:${radiusM}:${plz?.trim() ?? ""}`;
}

function fetchCached(
  lat: number,
  lon: number,
  radiusM: number,
  plz: string | undefined,
  signal?: AbortSignal,
): Promise<OsmNearbyResponse> {
  const key = makeCacheKey(lat, lon, radiusM, plz);
  const cached = cache.get(key);
  if (cached) return cached;
  const request = fetchOsmNearby({ lat, lon, plz, radiusM }, signal).catch((err) => {
    cache.delete(key);
    throw err;
  });
  cache.set(key, request);
  return request;
}

/**
 * Laedt OSM-Infrastrukturhinweise fuer einen aufgeloesten Projektstandort.
 */
export function useOsmNearby(
  lat: number | null,
  lon: number | null,
  options?: { enabled?: boolean; radiusM?: number; plz?: string },
): OsmNearbyStatus {
  const enabled = options?.enabled ?? true;
  const radiusM = options?.radiusM ?? 2500;
  const plz = options?.plz;
  const [status, setStatus] = useState<OsmNearbyStatus>({ kind: "idle" });

  useEffect(() => {
    if (!enabled || lat === null || lon === null || !Number.isFinite(lat) || !Number.isFinite(lon)) {
      setStatus({ kind: "idle" });
      return;
    }

    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      setStatus({ kind: "loading" });
      fetchCached(lat, lon, radiusM, plz, ctrl.signal)
        .then((data) => {
          if (ctrl.signal.aborted) return;
          setStatus({ kind: "ok", data });
        })
        .catch((err: unknown) => {
          if (ctrl.signal.aborted) return;
          const message =
            err instanceof GeoApiError
              ? err.detail?.message ?? err.message
              : err instanceof Error
                ? err.message
                : "OSM-Infrastrukturhinweise konnten nicht geladen werden.";
          setStatus({ kind: "error", message });
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [enabled, lat, lon, plz, radiusM]);

  return status;
}

export function osmBadgeLabel(status: OsmNearbyStatus): string {
  switch (status.kind) {
    case "ok":
      return status.data.assets.length > 0
        ? `OSM-Nahbauten: ${status.data.assets.length} Hinweise (Klasse ${status.data.data_class})`
        : "OSM-Nahbauten: keine Treffer im Radius";
    case "loading":
      return "OSM-Nahbauten: werden geladen...";
    case "error":
      return "OSM-Nahbauten: Fehler beim Laden";
    default:
      return "OSM-Infrastrukturhinweise: nicht angebunden";
  }
}

export function osmBadgeTone(status: OsmNearbyStatus): "good" | "warn" | "neutral" {
  if (status.kind === "ok") {
    return status.data.assets.length > 0 ? "good" : "warn";
  }
  if (status.kind === "error") return "warn";
  if (status.kind === "loading") return "neutral";
  return "warn";
}
