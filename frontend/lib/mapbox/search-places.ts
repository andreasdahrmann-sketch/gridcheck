import { getMapboxToken } from "./config";
import { MapboxGeocodingError, type MapboxPostalLocation } from "./geocoding";

export type MapboxSearchResult = MapboxPostalLocation & { plz?: string; ort?: string };

const GEO_BASE = "https://api.mapbox.com/geocoding/v5/mapbox.places";

type MapboxFeature = {
  center?: [number, number];
  place_name?: string;
  place_type?: string[];
  context?: Array<{ id?: string; text?: string; short_code?: string }>;
};

type MapboxResponse = {
  features?: MapboxFeature[];
};

function extractPlzOrt(feature: MapboxFeature): { plz?: string; ort?: string } {
  let plz: string | undefined;
  let ort: string | undefined;
  for (const entry of feature.context ?? []) {
    if (entry.id?.startsWith("postcode")) {
      plz = entry.text;
    }
    if (entry.id?.startsWith("place") || entry.id?.startsWith("locality")) {
      ort = entry.text;
    }
  }
  return { plz, ort };
}

function inferAccuracy(featureType?: string): MapboxPostalLocation["accuracy"] {
  if (featureType === "address") return "address";
  if (featureType === "postcode") return "postcode";
  if (featureType === "place" || featureType === "locality") return "place";
  if (featureType === "region") return "region";
  return "unknown";
}

/** Forward geocoding for address search (Germany). */
export async function searchMapboxPlaces(
  query: string,
  options?: { plz?: string; ort?: string; signal?: AbortSignal; limit?: number },
): Promise<MapboxSearchResult[]> {
  const trimmed = query.trim();
  if (trimmed.length < 3) {
    return [];
  }

  const token = getMapboxToken();
  if (!token) {
    throw new MapboxGeocodingError(
      "TOKEN_MISSING",
      "NEXT_PUBLIC_MAPBOX_TOKEN fehlt. Adresssuche ist nicht verfuegbar.",
    );
  }

  const params = new URLSearchParams({
    access_token: token,
    autocomplete: "true",
    country: "de",
    language: "de",
    limit: String(options?.limit ?? 5),
    types: "address,place,locality,postcode",
  });

  if (options?.plz?.trim()) {
    params.set("proximity", "ip");
  }

  const res = await fetch(`${GEO_BASE}/${encodeURIComponent(trimmed)}.json?${params.toString()}`, {
    method: "GET",
    signal: options?.signal,
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new MapboxGeocodingError("LOOKUP_FAILED", `Adresssuche fehlgeschlagen (HTTP ${res.status}).`);
  }

  const body = (await res.json()) as MapboxResponse;

  return (body.features ?? [])
    .filter(
      (feature) =>
        Array.isArray(feature.center) &&
        feature.center.length >= 2 &&
        Number.isFinite(feature.center[0]) &&
        Number.isFinite(feature.center[1]),
    )
    .map((feature) => {
      const [lng, lat] = feature.center as [number, number];
      const { plz, ort } = extractPlzOrt(feature);
      return {
        lng,
        lat,
        label: feature.place_name ?? trimmed,
        accuracy: inferAccuracy(feature.place_type?.[0]),
        featureType: feature.place_type?.[0] ?? "unknown",
        ...(plz ? { plz } : {}),
        ...(ort ? { ort } : {}),
      };
    });
}
