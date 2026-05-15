"use client";

import { useEffect, useState } from "react";
import {
  MapboxGeocodingError,
  geocodeProjectLocation,
  type MapboxAccuracy,
  type ProjectLocationSource,
} from "./geocoding";
import type { ProjectLocationInput } from "@/types";

export interface ResolvedProjectLocation {
  lat: number;
  lng: number;
  label: string;
  detail: string;
  source: ProjectLocationSource;
  accuracy: MapboxAccuracy | "coordinates";
  approximate: boolean;
  areaRadiusM: number;
}

export type ProjectLocationStatus =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; data: ResolvedProjectLocation }
  | { kind: "error"; message: string; code?: string };

const DEBOUNCE_MS = 250;
const cache = new Map<string, Promise<ResolvedProjectLocation>>();

function isFiniteCoordinate(value: number | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function inferAreaRadius(
  source: ProjectLocationSource,
  manualRadius?: number,
): number {
  const normalizedManual =
    typeof manualRadius === "number" && Number.isFinite(manualRadius) && manualRadius > 0
      ? manualRadius
      : undefined;

  switch (source) {
    case "coordinates":
      return normalizedManual ?? 0;
    case "address":
      return normalizedManual ?? 180;
    case "ort":
      return normalizedManual ?? 900;
    case "plz":
      return normalizedManual ?? 2200;
  }
}

function makeCacheKey(
  plz: string,
  ort?: string,
  location?: ProjectLocationInput,
): string {
  return [
    plz.trim(),
    ort?.trim().toLowerCase() ?? "",
    location?.address_hint?.trim().toLowerCase() ?? "",
    location?.latitude ?? "",
    location?.longitude ?? "",
    location?.area_radius_m ?? "",
  ].join("::");
}

function resolveFromCoordinates(location?: ProjectLocationInput): ResolvedProjectLocation | null {
  if (!location) return null;
  const latitude = location.latitude;
  const longitude = location.longitude;

  if (!isFiniteCoordinate(latitude) || !isFiniteCoordinate(longitude)) {
    return null;
  }

  if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    return null;
  }

  return {
    lat: latitude,
    lng: longitude,
    label: location.address_hint?.trim() || `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`,
    detail: "Exakter Projektstandort aus explizit hinterlegten Koordinaten.",
    source: "coordinates",
    accuracy: "coordinates",
    approximate: false,
    areaRadiusM: inferAreaRadius("coordinates", location.area_radius_m),
  };
}

function fetchCached(
  plz: string,
  ort?: string,
  location?: ProjectLocationInput,
  signal?: AbortSignal,
): Promise<ResolvedProjectLocation> {
  const key = makeCacheKey(plz, ort, location);
  const cached = cache.get(key);
  if (cached) return cached;

  const next = geocodeProjectLocation({
    plz,
    ort,
    addressHint: location?.address_hint,
    signal,
  })
    .then((result) => ({
      lat: result.lat,
      lng: result.lng,
      label: result.label,
      detail:
        result.source === "address"
          ? "Projektlage aus Adress-/Standorthinweis mit Mapbox-Geocoding."
          : result.source === "ort"
            ? "Projektlage aus Ort und PLZ mit Mapbox-Geocoding."
            : "Projektlage aus PLZ-Geocoding.",
      source: result.source,
      accuracy: result.accuracy,
      approximate: result.source !== "address" || result.accuracy !== "address",
      areaRadiusM: inferAreaRadius(result.source, location?.area_radius_m),
    }))
    .catch((error) => {
      cache.delete(key);
      throw error;
    });

  cache.set(key, next);
  return next;
}

export function useProjectLocation(
  plz: string,
  ort?: string,
  location?: ProjectLocationInput,
): ProjectLocationStatus {
  const [status, setStatus] = useState<ProjectLocationStatus>({ kind: "idle" });

  useEffect(() => {
    const direct = resolveFromCoordinates(location);
    if (direct) {
      setStatus({ kind: "ok", data: direct });
      return;
    }

    const trimmedPlz = plz.trim();
    if (!/^\d{5}$/.test(trimmedPlz)) {
      setStatus({ kind: "idle" });
      return;
    }

    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      setStatus({ kind: "loading" });
      fetchCached(trimmedPlz, ort, location, ctrl.signal)
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
            message:
              error instanceof Error ? error.message : "Unbekannter Fehler bei der Standortaufloesung.",
          });
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [location, ort, plz]);

  return status;
}
