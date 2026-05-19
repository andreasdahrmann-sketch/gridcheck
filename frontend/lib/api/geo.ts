// Frontend-Adapter fuer das Backend-Geo-Endpoint /api/v1/geo/plz/{plz}.
// Konsumiert die in backend/geo/schemas.py definierte Antwortstruktur.
// Proxying laeuft ueber next.config.mjs (rewrite /api/backend/:path*).

export interface VnbCandidate {
  name: string;
  kuerzel: string;
  snap_verfuegbar: boolean;
  snap_url: string | null;
  hinweis: string | null;
}

export interface PlzLookupResponse {
  plz: string;
  bundesland_kandidaten: string[];
  vnb_kandidaten: VnbCandidate[];
  snap_verfuegbar: boolean;
  confidence: string;
  quelle: string;
  stand: string;
  hinweis: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  hint: string | null;
}

export class GeoApiError extends Error {
  readonly status: number;
  readonly detail: ApiErrorDetail | null;

  constructor(status: number, detail: ApiErrorDetail | null, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

const BASE = "/api/backend/api/v1/geo";

export async function lookupPlz(
  plz: string,
  signal?: AbortSignal,
): Promise<PlzLookupResponse> {
  const trimmed = plz.trim();
  if (!/^\d{5}$/.test(trimmed)) {
    throw new GeoApiError(
      422,
      { code: "PLZ_INVALID", message: "PLZ muss aus 5 Ziffern bestehen.", hint: null },
      "PLZ muss aus 5 Ziffern bestehen.",
    );
  }

  const res = await fetch(`${BASE}/plz/${trimmed}`, {
    method: "GET",
    signal,
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    let detail: ApiErrorDetail | null = null;
    try {
      const body = await res.json();
      if (body && typeof body === "object" && body.detail) {
        const d = body.detail;
        detail = {
          code: typeof d.code === "string" ? d.code : "UNKNOWN",
          message: typeof d.message === "string" ? d.message : "Unbekannter Fehler",
          hint: typeof d.hint === "string" ? d.hint : null,
        };
      }
    } catch {
      // Body war kein JSON
    }
    throw new GeoApiError(
      res.status,
      detail,
      detail?.message ?? `Anfrage fehlgeschlagen (HTTP ${res.status}).`,
    );
  }

  return (await res.json()) as PlzLookupResponse;
}

export interface OsmNearbyAsset {
  type: string;
  name: string | null;
  lat: number;
  lon: number;
  distance_m: number;
  osm_id: string | null;
  tags_summary: string | null;
}

export interface OsmNearbyResponse {
  center_lat: number;
  center_lon: number;
  radius_m: number;
  plz: string | null;
  assets: OsmNearbyAsset[];
  source: string;
  data_class: string;
  confidence: string;
  confidence_score: number;
  confidence_geometrisch: number;
  confidence_technisch: number;
  quelle: string;
  hinweis: string;
  disclaimer: string;
  validierungsstatus: string;
  fetched_at: string;
  cache_hit: boolean;
}

export interface FetchOsmNearbyParams {
  lat?: number;
  lon?: number;
  plz?: string;
  radiusM?: number;
}

export async function fetchOsmNearby(
  params: FetchOsmNearbyParams,
  signal?: AbortSignal,
): Promise<OsmNearbyResponse> {
  const search = new URLSearchParams();
  if (params.lat !== undefined && params.lon !== undefined) {
    search.set("lat", String(params.lat));
    search.set("lon", String(params.lon));
  }
  if (params.plz?.trim()) {
    search.set("plz", params.plz.trim());
  }
  search.set("radius_m", String(params.radiusM ?? 2500));

  const res = await fetch(`${BASE}/osm-nearby?${search.toString()}`, {
    method: "GET",
    signal,
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    let detail: ApiErrorDetail | null = null;
    try {
      const body = await res.json();
      if (body && typeof body === "object" && body.detail) {
        const d = body.detail;
        detail = {
          code: typeof d.code === "string" ? d.code : "UNKNOWN",
          message: typeof d.message === "string" ? d.message : "Unbekannter Fehler",
          hint: typeof d.hint === "string" ? d.hint : null,
        };
      }
    } catch {
      // Body war kein JSON
    }
    throw new GeoApiError(
      res.status,
      detail,
      detail?.message ?? `OSM-Abfrage fehlgeschlagen (HTTP ${res.status}).`,
    );
  }

  return (await res.json()) as OsmNearbyResponse;
}
