import { getMapboxToken } from "./config";

export type MapboxAccuracy = "postcode" | "place" | "locality" | "address" | "region" | "unknown";
export type ProjectLocationSource = "coordinates" | "address" | "ort" | "plz";

export interface MapboxPostalLocation {
  lng: number;
  lat: number;
  label: string;
  accuracy: MapboxAccuracy;
  featureType: string;
}

export interface ProjectLocationGeocode extends MapboxPostalLocation {
  source: Exclude<ProjectLocationSource, "coordinates">;
  query: string;
}

type MapboxFeature = {
  center?: [number, number];
  text?: string;
  place_name?: string;
  place_type?: string[];
  relevance?: number;
  context?: Array<{
    id?: string;
    text?: string;
    short_code?: string;
  }>;
};

type MapboxResponse = {
  features?: MapboxFeature[];
};

type GeocodingErrorCode = "TOKEN_MISSING" | "LOOKUP_FAILED" | "NO_RESULT" | "INPUT_INVALID";

const GEO_BASE = "https://api.mapbox.com/geocoding/v5/mapbox.places";

export class MapboxGeocodingError extends Error {
  readonly code: GeocodingErrorCode;

  constructor(code: GeocodingErrorCode, message: string) {
    super(message);
    this.code = code;
  }
}

function inferAccuracy(featureType?: string): MapboxAccuracy {
  switch (featureType) {
    case "postcode":
      return "postcode";
    case "place":
      return "place";
    case "locality":
      return "locality";
    case "address":
      return "address";
    case "region":
      return "region";
    default:
      return "unknown";
  }
}

function compactParts(parts: Array<string | undefined>): string[] {
  return parts.map((value) => value?.trim()).filter(Boolean) as string[];
}

function buildAddressQuery(addressHint: string, ort?: string, plz?: string): string {
  return compactParts([addressHint, ort, plz]).join(", ");
}

function scoreFeature(
  feature: MapboxFeature,
  options: {
    plz?: string;
    ort?: string;
    addressHint?: string;
    preferAddress?: boolean;
  },
): number {
  const { plz, ort, addressHint, preferAddress } = options;
  let score = feature.relevance ?? 0;
  const featureType = feature.place_type?.[0];
  const label = `${feature.text ?? ""} ${feature.place_name ?? ""}`.toLowerCase();
  const normalizedOrt = ort?.trim().toLowerCase();
  const normalizedAddress = addressHint?.trim().toLowerCase();

  if (preferAddress && featureType === "address") score += 3;
  if (featureType === "postcode") score += 4;
  if (plz && feature.text?.trim() === plz) score += 3;
  if (plz && label.includes(plz)) score += 1.5;
  if (normalizedOrt && label.includes(normalizedOrt)) score += 1;
  if (normalizedAddress && label.includes(normalizedAddress)) score += 2.5;
  if (feature.context?.some((entry) => entry.short_code?.toLowerCase() === "de")) {
    score += 0.5;
  }

  return score;
}

async function geocodeQuery(
  query: string,
  options: {
    plz?: string;
    ort?: string;
    addressHint?: string;
    preferAddress?: boolean;
    signal?: AbortSignal;
  },
): Promise<MapboxPostalLocation> {
  if (!query.trim()) {
    throw new MapboxGeocodingError("INPUT_INVALID", "Leerer Standort-Query fuer Mapbox-Geocoding.");
  }

  const token = getMapboxToken();
  if (!token) {
    throw new MapboxGeocodingError(
      "TOKEN_MISSING",
      "NEXT_PUBLIC_MAPBOX_TOKEN fehlt. Mapbox-Geocoding kann nicht gestartet werden.",
    );
  }

  const params = new URLSearchParams({
    access_token: token,
    autocomplete: "false",
    country: "de",
    language: "de",
    limit: "5",
    types: "postcode,place,locality,address,region",
  });

  const res = await fetch(`${GEO_BASE}/${encodeURIComponent(query)}.json?${params.toString()}`, {
    method: "GET",
    signal: options.signal,
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new MapboxGeocodingError(
      "LOOKUP_FAILED",
      `Mapbox-Geocoding fehlgeschlagen (HTTP ${res.status}).`,
    );
  }

  const body = (await res.json()) as MapboxResponse;
  const feature = (body.features ?? [])
    .filter(
      (candidate) =>
        Array.isArray(candidate.center) &&
        candidate.center.length >= 2 &&
        Number.isFinite(candidate.center[0]) &&
        Number.isFinite(candidate.center[1]),
    )
    .sort(
      (left, right) =>
        scoreFeature(right, options) - scoreFeature(left, options),
    )[0];

  if (!feature?.center) {
    throw new MapboxGeocodingError(
      "NO_RESULT",
      "Fuer diesen Standort konnte kein Mapbox-Kartenausschnitt gefunden werden.",
    );
  }

  const [lng, lat] = feature.center;

  return {
    lng,
    lat,
    label: feature.place_name ?? query,
    accuracy: inferAccuracy(feature.place_type?.[0]),
    featureType: feature.place_type?.[0] ?? "unknown",
  };
}

function buildOrtQuery(plz: string, ort?: string): string {
  const parts = [plz.trim(), ort?.trim()].filter(Boolean);
  return parts.join(" ");
}

export async function geocodePostalArea(
  plz: string,
  ort?: string,
  signal?: AbortSignal,
): Promise<MapboxPostalLocation> {
  const trimmedPlz = plz.trim();
  if (!/^\d{5}$/.test(trimmedPlz)) {
    throw new MapboxGeocodingError("INPUT_INVALID", "PLZ muss aus 5 Ziffern bestehen.");
  }

  return geocodeQuery(buildOrtQuery(trimmedPlz, ort), {
    plz: trimmedPlz,
    ort,
    signal,
  });
}

export async function geocodeProjectLocation(
  options: {
    plz: string;
    ort?: string;
    addressHint?: string;
    signal?: AbortSignal;
  },
): Promise<ProjectLocationGeocode> {
  const trimmedPlz = options.plz.trim();
  if (!/^\d{5}$/.test(trimmedPlz)) {
    throw new MapboxGeocodingError("INPUT_INVALID", "PLZ muss aus 5 Ziffern bestehen.");
  }

  const addressHint = options.addressHint?.trim();
  const ort = options.ort?.trim();

  if (addressHint) {
    const query = buildAddressQuery(addressHint, ort, trimmedPlz);
    const location = await geocodeQuery(query, {
      plz: trimmedPlz,
      ort,
      addressHint,
      preferAddress: true,
      signal: options.signal,
    });
    return {
      ...location,
      source: "address",
      query,
    };
  }

  if (ort) {
    const query = buildOrtQuery(trimmedPlz, ort);
    const location = await geocodeQuery(query, {
      plz: trimmedPlz,
      ort,
      signal: options.signal,
    });
    return {
      ...location,
      source: "ort",
      query,
    };
  }

  const location = await geocodeQuery(trimmedPlz, {
    plz: trimmedPlz,
    signal: options.signal,
  });
  return {
    ...location,
    source: "plz",
    query: trimmedPlz,
  };
}
