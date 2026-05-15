"use client";

import { useEffect, useState } from "react";
import {
  MapboxGeocodingError,
  geocodePostalArea,
  type MapboxPostalLocation,
} from "./geocoding";

export type PlzGeocodeStatus =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; data: MapboxPostalLocation }
  | { kind: "error"; message: string; code?: string };

const DEBOUNCE_MS = 250;
const cache = new Map<string, Promise<MapboxPostalLocation>>();

function makeCacheKey(plz: string, ort?: string): string {
  return `${plz.trim()}::${ort?.trim().toLowerCase() ?? ""}`;
}

function fetchCached(
  plz: string,
  ort?: string,
  signal?: AbortSignal,
): Promise<MapboxPostalLocation> {
  const key = makeCacheKey(plz, ort);
  const cached = cache.get(key);
  if (cached) return cached;

  const next = geocodePostalArea(plz, ort, signal).catch((error) => {
    cache.delete(key);
    throw error;
  });

  cache.set(key, next);
  return next;
}

export function usePlzGeocode(plz: string, ort?: string): PlzGeocodeStatus {
  const [status, setStatus] = useState<PlzGeocodeStatus>({ kind: "idle" });

  useEffect(() => {
    const trimmed = plz.trim();
    if (!/^\d{5}$/.test(trimmed)) {
      setStatus({ kind: "idle" });
      return;
    }

    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      setStatus({ kind: "loading" });
      fetchCached(trimmed, ort, ctrl.signal)
        .then((data) => {
          if (ctrl.signal.aborted) return;
          setStatus({ kind: "ok", data });
        })
        .catch((error: unknown) => {
          if (ctrl.signal.aborted) return;

          if (error instanceof MapboxGeocodingError) {
            setStatus({ kind: "error", message: error.message, code: error.code });
            return;
          }

          setStatus({
            kind: "error",
            message: error instanceof Error ? error.message : "Unbekannter Fehler beim Mapbox-Geocoding.",
          });
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [plz, ort]);

  return status;
}
