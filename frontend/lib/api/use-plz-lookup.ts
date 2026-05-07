"use client";

import { useEffect, useState } from "react";
import {
  GeoApiError,
  lookupPlz,
  type PlzLookupResponse,
} from "./geo";

export type PlzLookupStatus =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; data: PlzLookupResponse }
  | { kind: "error"; message: string };

const DEBOUNCE_MS = 350;

// Simpler In-Memory-Cache pro PLZ. Verhindert doppelte Netzaufrufe bei
// wiederholten Lookups auf dieselbe PLZ. Nicht persistiert.
const cache = new Map<string, Promise<PlzLookupResponse>>();

function fetchCached(plz: string, signal?: AbortSignal): Promise<PlzLookupResponse> {
  const cached = cache.get(plz);
  if (cached) return cached;
  const p = lookupPlz(plz, signal).catch((err) => {
    cache.delete(plz);
    throw err;
  });
  cache.set(plz, p);
  return p;
}

/**
 * Reagiert auf PLZ-Aenderungen mit Debounce und liefert den aktuellen
 * Lookup-Status. Sobald die PLZ nicht mehr genau 5 Ziffern hat,
 * wird der Status auf "idle" zurueckgesetzt.
 */
export function usePlzLookup(plz: string): PlzLookupStatus {
  const [status, setStatus] = useState<PlzLookupStatus>({ kind: "idle" });

  useEffect(() => {
    const trimmed = plz.trim();
    if (!/^\d{5}$/.test(trimmed)) {
      setStatus({ kind: "idle" });
      return;
    }

    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      setStatus({ kind: "loading" });
      fetchCached(trimmed, ctrl.signal)
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
                : "Unbekannter Fehler bei VNB-Lookup.";
          setStatus({ kind: "error", message });
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [plz]);

  return status;
}
