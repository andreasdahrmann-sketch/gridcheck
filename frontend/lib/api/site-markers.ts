import { getCsrfTokenFromCookie } from "@/lib/api/csrf";

export type SiteMarkerAssetType = "ortsnetztrafo" | "umspannwerk" | "schaltstation";
export type SiteMarkerLocationSource = "gps" | "manual";

export type SiteMarker = {
  id: number;
  asset_type: SiteMarkerAssetType;
  location_source: SiteMarkerLocationSource;
  verification_status: "unverified";
  latitude: number;
  longitude: number;
  photo_file_name: string;
  photo_mime_type: string;
  photo_size_bytes: number;
  photo_api_path: string;
  revision_hash?: string | null;
  created_at: string;
};

const BASE = "/api/backend/api/v1/site-markers";

export class SiteMarkerApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "SiteMarkerApiError";
    this.status = status;
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new SiteMarkerApiError(body?.detail?.message ?? "API request failed", res.status);
  }
  return res.json() as Promise<T>;
}

export async function listSiteMarkers() {
  const res = await fetch(BASE, { credentials: "include", cache: "no-store" });
  return parse<SiteMarker[]>(res);
}

export async function createSiteMarker(payload: {
  asset_type: SiteMarkerAssetType;
  location_source: SiteMarkerLocationSource;
  latitude: number;
  longitude: number;
  photo: File;
}) {
  const formData = new FormData();
  formData.set("asset_type", payload.asset_type);
  formData.set("location_source", payload.location_source);
  formData.set("latitude", String(payload.latitude));
  formData.set("longitude", String(payload.longitude));
  formData.set("photo", payload.photo);

  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(BASE, {
    method: "POST",
    credentials: "include",
    headers: { ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
    body: formData,
  });
  return parse<SiteMarker>(res);
}

export function getSiteMarkerPhotoUrl(photoApiPath: string) {
  return `/api/backend${photoApiPath}`;
}
