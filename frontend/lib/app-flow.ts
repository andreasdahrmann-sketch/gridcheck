type SearchParamsReader = {
  get: (name: string) => string | null;
};

export type SiteMarkerFlowContext = {
  source?: "project" | "check";
  projectId?: number | null;
  projectName?: string | null;
  plz?: string | null;
  ort?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  returnTo?: string | null;
  assetType?: string | null;
};

export type ParsedSiteMarkerFlowContext = {
  source?: string;
  projectId?: number;
  projectName?: string;
  plz?: string;
  ort?: string;
  latitude?: number;
  longitude?: number;
  returnTo?: string;
  assetType?: string;
};

function appendParam(params: URLSearchParams, key: string, value: string | number | null | undefined) {
  if (value === undefined || value === null) {
    return;
  }

  const normalized = String(value).trim();
  if (!normalized) {
    return;
  }

  params.set(key, normalized);
}

function readNumber(value: string | null) {
  if (!value) {
    return undefined;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function buildSiteMarkerHref(context: SiteMarkerFlowContext) {
  const params = new URLSearchParams();

  appendParam(params, "source", context.source);
  appendParam(params, "projectId", context.projectId);
  appendParam(params, "projectName", context.projectName);
  appendParam(params, "plz", context.plz);
  appendParam(params, "ort", context.ort);
  appendParam(params, "latitude", context.latitude);
  appendParam(params, "longitude", context.longitude);
  appendParam(params, "returnTo", context.returnTo);
  appendParam(params, "assetType", context.assetType);

  const query = params.toString();
  return query ? `/site-markers?${query}` : "/site-markers";
}

export function parseSiteMarkerFlowContext(searchParams: SearchParamsReader): ParsedSiteMarkerFlowContext {
  return {
    source: searchParams.get("source") ?? undefined,
    projectId: readNumber(searchParams.get("projectId")),
    projectName: searchParams.get("projectName") ?? undefined,
    plz: searchParams.get("plz") ?? undefined,
    ort: searchParams.get("ort") ?? undefined,
    latitude: readNumber(searchParams.get("latitude")),
    longitude: readNumber(searchParams.get("longitude")),
    returnTo: searchParams.get("returnTo") ?? undefined,
    assetType: searchParams.get("assetType") ?? undefined,
  };
}
