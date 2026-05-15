const DEFAULT_MAPBOX_STYLE_ID = "mapbox/dark-v11";

function normalizeStyleId(raw?: string): string {
  const value = raw?.trim();
  if (!value) return DEFAULT_MAPBOX_STYLE_ID;
  if (value.startsWith("mapbox://styles/")) {
    return value.slice("mapbox://styles/".length);
  }
  return value;
}

export function getMapboxToken(): string {
  return process.env.NEXT_PUBLIC_MAPBOX_TOKEN?.trim() ?? "";
}

export function hasMapboxToken(): boolean {
  return getMapboxToken().length > 0;
}

export function getMapboxStyleId(): string {
  return normalizeStyleId(
    process.env.NEXT_PUBLIC_MAPBOX_STYLE_ID ?? process.env.NEXT_PUBLIC_MAPBOX_STYLE,
  );
}

export function getMapboxTileUrl(): string | null {
  const token = getMapboxToken();
  if (!token) return null;
  return `https://api.mapbox.com/styles/v1/${getMapboxStyleId()}/tiles/512/{z}/{x}/{y}@2x?access_token=${token}`;
}
