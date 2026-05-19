"""OSM/Overpass-Umkreissuche fuer Infrastrukturhinweise (Nahbauten).

Liefert normalisierte Asset-Hinweise aus OpenStreetMap. Keine Kapazitaetsaussagen.
Siehe docs/OSM_FETCH_STUB.md.
"""
from __future__ import annotations

import json
import math
import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode

import httpx

from core.errors import AnalysisError

from .schemas import OsmNearbyAsset, OsmNearbyResponse

_DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "GridCheck-PreNetzcheck/1.0 (contact: dev@gridcheck.local)"

DISCLAIMER = (
    "OpenStreetMap-Hinweise sind Community-Daten, nicht verifiziert und ersetzen "
    "keine Netzbetreiber-Auskunft. Keine Aussage zur freien Netzkapazitaet oder "
    "Anschlussfaehigkeit."
)
HINWEIS = "OSM — Infrastrukturhinweise nur zur Lageorientierung; keine Kapazitaetsaussage."

_CACHE: dict[str, tuple[float, OsmNearbyResponse]] = {}
_RATE_TIMESTAMPS: deque[float] = deque()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def overpass_url() -> str:
    return os.getenv("OSM_OVERPASS_URL", _DEFAULT_OVERPASS_URL).strip() or _DEFAULT_OVERPASS_URL


def fetch_timeout_sec() -> int:
    return max(5, _env_int("OSM_FETCH_TIMEOUT_SEC", 25))


def rate_limit_per_min() -> int:
    return max(1, _env_int("OSM_RATE_LIMIT_PER_MIN", 6))


def cache_ttl_sec() -> int:
    return max(30, _env_int("OSM_NEARBY_CACHE_TTL_SEC", 300))


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_plz(raw: str | None) -> str | None:
    if raw is None:
        return None
    candidate = str(raw).strip()
    if len(candidate) != 5 or not candidate.isdigit():
        raise AnalysisError(
            code="PLZ_INVALID",
            message=f"PLZ '{raw}' ist ungueltig.",
            hint="Erwartet werden genau 5 Ziffern, z. B. 04109.",
            http_status=422,
        )
    return candidate


def _validate_radius(radius_m: int) -> int:
    if radius_m < 100 or radius_m > 15_000:
        raise AnalysisError(
            code="RADIUS_INVALID",
            message=f"radius_m={radius_m} liegt ausserhalb des erlaubten Bereichs.",
            hint="Erlaubt sind 100 bis 15000 Meter.",
            http_status=422,
        )
    return radius_m


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * earth_radius_m * math.asin(math.sqrt(a))


def bbox_from_center(lat: float, lon: float, radius_m: int) -> tuple[float, float, float, float]:
    lat_delta = radius_m / 111_320.0
    cos_lat = math.cos(math.radians(lat)) or 1e-6
    lon_delta = radius_m / (111_320.0 * cos_lat)
    return (
        lat - lat_delta,
        lon - lon_delta,
        lat + lat_delta,
        lon + lon_delta,
    )


def build_overpass_query(south: float, west: float, north: float, east: float) -> str:
    return f"""[out:json][timeout:25];
(
  node["power"~"substation|transformer|tower|pole"]({south},{west},{north},{east});
  way["power"~"substation|line|minor_line|cable"]({south},{west},{north},{east});
);
out center tags;"""


def _normalize_asset_type(tags: dict[str, Any]) -> str:
    power = str(tags.get("power") or "").lower()
    if power in {"substation"}:
        return "substation"
    if power in {"transformer"}:
        return "transformer"
    if power in {"line", "minor_line", "cable"}:
        return "power_line"
    if power in {"tower", "pole"}:
        return "support"
    return power or "unknown"


def _asset_name(tags: dict[str, Any]) -> str | None:
    for key in ("name", "ref", "operator", "substation"):
        value = tags.get(key)
        if value:
            return str(value)
    return None


def _tags_summary(tags: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for key in ("power", "voltage", "substation", "operator"):
        if key in tags and tags[key]:
            parts.append(f"{key}={tags[key]}")
    if not parts:
        return None
    return ", ".join(parts[:4])


def _element_position(element: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def parse_overpass_elements(
    elements: list[dict[str, Any]],
    *,
    center_lat: float,
    center_lon: float,
    radius_m: int,
) -> list[OsmNearbyAsset]:
    assets: list[OsmNearbyAsset] = []
    seen: set[str] = set()

    for element in elements:
        if element.get("type") not in {"node", "way", "relation"}:
            continue
        tags = element.get("tags") or {}
        if not tags.get("power"):
            continue
        position = _element_position(element)
        if position is None:
            continue
        lat, lon = position
        distance_m = haversine_distance_m(center_lat, center_lon, lat, lon)
        if distance_m > radius_m:
            continue

        element_type = element.get("type", "node")
        osm_id = f"{element_type}/{element.get('id')}"
        if osm_id in seen:
            continue
        seen.add(osm_id)

        assets.append(
            OsmNearbyAsset(
                type=_normalize_asset_type(tags),
                name=_asset_name(tags),
                lat=round(lat, 6),
                lon=round(lon, 6),
                distance_m=round(distance_m, 1),
                osm_id=osm_id,
                tags_summary=_tags_summary(tags),
            ),
        )

    assets.sort(key=lambda item: item.distance_m)
    return assets


def _cache_key(lat: float, lon: float, radius_m: int) -> str:
    return f"{round(lat, 5)}:{round(lon, 5)}:{radius_m}"


def _check_rate_limit() -> None:
    now = time.monotonic()
    window = 60.0
    limit = rate_limit_per_min()
    while _RATE_TIMESTAMPS and now - _RATE_TIMESTAMPS[0] > window:
        _RATE_TIMESTAMPS.popleft()
    if len(_RATE_TIMESTAMPS) >= limit:
        raise AnalysisError(
            code="OSM_RATE_LIMIT",
            message="Zu viele OSM-Abfragen in kurzer Zeit.",
            hint="Bitte einen Moment warten und erneut versuchen.",
            http_status=429,
        )
    _RATE_TIMESTAMPS.append(now)


def _get_cached(key: str) -> OsmNearbyResponse | None:
    entry = _CACHE.get(key)
    if not entry:
        return None
    expires_at, payload = entry
    if time.monotonic() > expires_at:
        _CACHE.pop(key, None)
        return None
    cached = payload.model_copy(deep=True)
    cached.cache_hit = True
    return cached


def _set_cache(key: str, payload: OsmNearbyResponse) -> None:
    _CACHE[key] = (time.monotonic() + cache_ttl_sec(), payload.model_copy(deep=True))


def _http_post_json(url: str, *, data: str, headers: dict[str, str]) -> dict[str, Any]:
    with httpx.Client(timeout=fetch_timeout_sec()) as client:
        response = client.post(url, content=data, headers=headers)
        response.raise_for_status()
        return response.json()


def _http_get_json(url: str, *, params: dict[str, str], headers: dict[str, str]) -> list[dict[str, Any]]:
    with httpx.Client(timeout=fetch_timeout_sec()) as client:
        response = client.get(url, params=params, headers=headers)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list):
            return []
        return body


def fetch_overpass(
    lat: float,
    lon: float,
    radius_m: int,
    *,
    post_json: Callable[..., dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    south, west, north, east = bbox_from_center(lat, lon, radius_m)
    query = build_overpass_query(south, west, north, east)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": _USER_AGENT,
    }
    poster = post_json or _http_post_json
    payload = poster(
        overpass_url(),
        data=urlencode({"data": query}),
        headers=headers,
    )
    elements = payload.get("elements")
    if not isinstance(elements, list):
        return []
    return elements


def geocode_plz_center(plz: str, *, get_json: Callable[..., list[dict[str, Any]]] | None = None) -> tuple[float, float]:
    getter = get_json or _http_get_json
    results = getter(
        os.getenv("OSM_NOMINATIM_URL", _DEFAULT_NOMINATIM_URL).strip() or _DEFAULT_NOMINATIM_URL,
        params={
            "postalcode": plz,
            "country": "DE",
            "format": "json",
            "limit": "1",
        },
        headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
    )
    if not results:
        raise AnalysisError(
            code="PLZ_GEOCODE_FAILED",
            message=f"Kein Geocoding-Treffer fuer PLZ {plz}.",
            hint="Bitte lat und lon direkt angeben.",
            http_status=422,
        )
    first = results[0]
    return float(first["lat"]), float(first["lon"])


def lookup_osm_nearby(
    *,
    lat: float | None = None,
    lon: float | None = None,
    plz: str | None = None,
    radius_m: int = 2_500,
    overpass_fetch: Callable[[float, float, int], list[dict[str, Any]]] | None = None,
    plz_geocode: Callable[[str], tuple[float, float]] | None = None,
) -> OsmNearbyResponse:
    radius = _validate_radius(radius_m)
    normalized_plz = _normalize_plz(plz)

    center_lat: float | None = lat
    center_lon: float | None = lon

    if center_lat is not None and center_lon is not None:
        if not (-90.0 <= center_lat <= 90.0 and -180.0 <= center_lon <= 180.0):
            raise AnalysisError(
                code="COORDINATES_INVALID",
                message="lat/lon ausserhalb des gueltigen Bereichs.",
                hint="lat zwischen -90 und 90, lon zwischen -180 und 180.",
                http_status=422,
            )
    elif normalized_plz:
        geocoder = plz_geocode or geocode_plz_center
        center_lat, center_lon = geocoder(normalized_plz)
    else:
        raise AnalysisError(
            code="LOCATION_REQUIRED",
            message="Entweder lat und lon oder plz sind erforderlich.",
            hint="Fuer die Netzplan-Karte lat/lon aus dem Projektstandort uebergeben.",
            http_status=422,
        )

    assert center_lat is not None and center_lon is not None

    cache_key = _cache_key(center_lat, center_lon, radius)
    cached = _get_cached(cache_key)
    if cached:
        if normalized_plz:
            cached.plz = normalized_plz
        return cached

    _check_rate_limit()

    validierungsstatus = "OK"
    assets: list[OsmNearbyAsset] = []
    try:
        fetcher = overpass_fetch or fetch_overpass
        elements = fetcher(center_lat, center_lon, radius)
        assets = parse_overpass_elements(
            elements,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_m=radius,
        )
        if not assets:
            validierungsstatus = "PARTIAL"
    except httpx.HTTPError as exc:
        validierungsstatus = "ERROR"
        raise AnalysisError(
            code="OSM_FETCH_FAILED",
            message="OSM/Overpass-Abfrage fehlgeschlagen.",
            hint=str(exc)[:180],
            http_status=502,
        ) from exc

    response = OsmNearbyResponse(
        center_lat=round(center_lat, 6),
        center_lon=round(center_lon, 6),
        radius_m=radius,
        plz=normalized_plz,
        assets=assets,
        source="OSM",
        data_class="B",
        confidence="B",
        confidence_score=60,
        confidence_geometrisch=60,
        confidence_technisch=45,
        quelle=f"OpenStreetMap via Overpass ({overpass_url()})",
        hinweis=HINWEIS if assets else f"{HINWEIS} Keine passenden power=*-Objekte im Radius gefunden.",
        disclaimer=DISCLAIMER,
        validierungsstatus=validierungsstatus,
        fetched_at=_now_iso(),
        cache_hit=False,
    )
    _set_cache(cache_key, response)
    return response


def clear_osm_nearby_cache_for_tests() -> None:
    _CACHE.clear()
    _RATE_TIMESTAMPS.clear()


SAMPLE_OVERPASS_RESPONSE: dict[str, Any] = {
    "elements": [
        {
            "type": "node",
            "id": 1001,
            "lat": 51.3401,
            "lon": 12.3734,
            "tags": {"power": "substation", "name": "Demo Umspannwerk", "voltage": "110000"},
        },
        {
            "type": "node",
            "id": 1002,
            "lat": 51.3415,
            "lon": 12.3750,
            "tags": {"power": "transformer", "operator": "Demo Netz AG"},
        },
    ],
}
