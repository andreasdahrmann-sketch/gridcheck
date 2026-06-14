"""Geocoding-Service fuer Projektstandorte (Adresse <-> WGS84-Koordinaten).

Provider: OpenStreetMap Nominatim (Datenklasse B, Community-Quelle).
- Konservativer In-Process-Rate-Limit: min. 1 s zwischen Nominatim-Aufrufen.
- In-Memory-LRU-Cache (max 1024 Eintraege) — Persistenz spaeter ueber Datenquellen-Pipeline.
- Fail-soft: bei Netzfehler / Timeout / Rate-Limit-Verletzung kein Exception, sondern `None`.
- Keine neue Dependency: nutzt `httpx` (wird bereits in backend/geo/osm_nearby.py verwendet).

Confidence-Mapping:
- Nominatim liefert ein `importance`-Feld (~0..1, oft 0.0..0.7) — wir mappen auf 0..100.
- Bei klarem Treffer mit Hausnummer (`addresstype == "building"` oder `class == "place"` + `house_number` vorhanden) wird ein Bonus addiert (max 100).

Lizenz / Attribution:
- OpenStreetMap Daten unter ODbL — Attribution beim Anzeigen / Reporting verpflichtend.
- Jede Antwort traegt `source = "OpenStreetMap (Nominatim)"` fuer das Projekt-Audit.

Hinweis Datenschutz:
- Adresseingaben werden zum Geocoding an die oeffentliche Nominatim-API geleitet
  (oder an eine selbst betriebene Instanz via NOMINATIM_URL).
- Nutzer muss dies im Frontend transparent vermittelt bekommen (siehe Frontend-Disclaimer).
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Any, Callable

import httpx


_DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
_DEFAULT_CONTACT_EMAIL = "dev@gridcheck.local"
_USER_AGENT_TEMPLATE = "GridCheck-PreNetzcheck/1.0 (contact: {contact})"

_SOURCE_LABEL = "OpenStreetMap (Nominatim)"
_DATA_CLASS = "B"

_MAX_CACHE_ENTRIES = 1024
_MIN_INTERVAL_SECONDS = 1.0
_DEFAULT_TIMEOUT_SECONDS = 8.0

_cache: "OrderedDict[str, dict[str, Any] | None]" = OrderedDict()
_cache_lock = threading.Lock()

_rate_lock = threading.Lock()
_last_request_monotonic = 0.0


def _user_agent() -> str:
    contact = os.getenv("GEOCODING_CONTACT_EMAIL", _DEFAULT_CONTACT_EMAIL).strip() or _DEFAULT_CONTACT_EMAIL
    return _USER_AGENT_TEMPLATE.format(contact=contact)


def _nominatim_base_url() -> str:
    return os.getenv("NOMINATIM_URL", _DEFAULT_NOMINATIM_URL).strip().rstrip("/") or _DEFAULT_NOMINATIM_URL


def _timeout_seconds() -> float:
    raw = os.getenv("GEOCODING_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS)).strip()
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS
    return max(1.0, min(value, 30.0))


def _cache_get(key: str) -> dict[str, Any] | None | object:
    sentinel = object()
    with _cache_lock:
        if key not in _cache:
            return sentinel
        value = _cache.pop(key)
        _cache[key] = value
        return value


def _cache_set(key: str, value: dict[str, Any] | None) -> None:
    with _cache_lock:
        if key in _cache:
            _cache.pop(key)
        _cache[key] = value
        while len(_cache) > _MAX_CACHE_ENTRIES:
            _cache.popitem(last=False)


def _respect_rate_limit() -> None:
    global _last_request_monotonic
    with _rate_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL_SECONDS - (now - _last_request_monotonic)
        if wait > 0:
            time.sleep(wait)
        _last_request_monotonic = time.monotonic()


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _confidence_from_importance(importance: Any, *, address_has_house_number: bool) -> int:
    try:
        score = float(importance)
    except (TypeError, ValueError):
        score = 0.0
    base = int(round(max(0.0, min(score, 1.0)) * 100))
    if address_has_house_number:
        base = min(100, base + 20)
    return max(0, min(100, base))


def _format_address_query(*, street: str | None, house_number: str | None, plz: str | None, city: str | None) -> str:
    parts: list[str] = []
    street_part = " ".join(filter(None, [_safe_str(street), _safe_str(house_number)]))
    if street_part:
        parts.append(street_part)
    locality = " ".join(filter(None, [_safe_str(plz), _safe_str(city)]))
    if locality:
        parts.append(locality)
    if not parts:
        return ""
    return ", ".join(parts)


def _http_get_json(
    url: str,
    *,
    params: dict[str, str],
    timeout_seconds: float,
    user_agent: str,
) -> Any:
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


def geocode_address(
    *,
    street: str | None = None,
    house_number: str | None = None,
    plz: str | None = None,
    city: str | None = None,
    country: str = "de",
    http_get_json: Callable[..., Any] | None = None,
) -> dict[str, Any] | None:
    """Adresse -> Koordinaten via Nominatim. Liefert None bei Fehlern / leeren Eingaben.

    Rueckgabe-Felder:
      latitude, longitude, confidence (0..100), source, data_class, raw_label, has_house_number
    """
    query = _format_address_query(street=street, house_number=house_number, plz=plz, city=city)
    if not query:
        return None
    cache_key = f"fwd::{country.lower()}::{query.lower()}"
    cached = _cache_get(cache_key)
    sentinel_missing = object()
    if cached is not sentinel_missing and cached is not None and isinstance(cached, dict):
        return dict(cached)
    if cached is None:
        return None

    getter = http_get_json or _http_get_json
    url = f"{_nominatim_base_url()}/search"
    params: dict[str, str] = {"format": "jsonv2", "limit": "1", "addressdetails": "1"}
    street_q = " ".join(filter(None, [_safe_str(street), _safe_str(house_number)]))
    if street_q:
        params["street"] = street_q
    if _safe_str(city):
        params["city"] = _safe_str(city) or ""
    if _safe_str(plz):
        params["postalcode"] = _safe_str(plz) or ""
    if country:
        params["countrycodes"] = country.lower()
    if not any(k in params for k in ("street", "city", "postalcode")):
        params["q"] = query

    _respect_rate_limit()
    try:
        payload = getter(
            url,
            params=params,
            timeout_seconds=_timeout_seconds(),
            user_agent=_user_agent(),
        )
    except Exception:
        _cache_set(cache_key, None)
        return None

    if not isinstance(payload, list) or not payload:
        _cache_set(cache_key, None)
        return None

    first = payload[0] if isinstance(payload[0], dict) else None
    if not first:
        _cache_set(cache_key, None)
        return None

    try:
        latitude = float(first["lat"])
        longitude = float(first["lon"])
    except (KeyError, TypeError, ValueError):
        _cache_set(cache_key, None)
        return None

    address_obj = first.get("address") if isinstance(first.get("address"), dict) else {}
    has_house_number = bool(address_obj.get("house_number"))
    confidence = _confidence_from_importance(first.get("importance"), address_has_house_number=has_house_number)

    result = {
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "confidence": confidence,
        "source": _SOURCE_LABEL,
        "data_class": _DATA_CLASS,
        "raw_label": _safe_str(first.get("display_name")),
        "has_house_number": has_house_number,
    }
    _cache_set(cache_key, result)
    return dict(result)


def reverse_geocode(
    *,
    lat: float | None,
    lon: float | None,
    http_get_json: Callable[..., Any] | None = None,
) -> dict[str, Any] | None:
    """Koordinaten -> Adresse via Nominatim. Liefert None bei Fehlern / unvollstaendigen Eingaben.

    Rueckgabe-Felder:
      street, house_number, plz, city, confidence, source, data_class, raw_label
    """
    if lat is None or lon is None:
        return None
    try:
        lat_value = float(lat)
        lon_value = float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= lat_value <= 90.0 and -180.0 <= lon_value <= 180.0):
        return None

    cache_key = f"rev::{round(lat_value, 6)}::{round(lon_value, 6)}"
    cached = _cache_get(cache_key)
    sentinel_missing = object()
    if cached is not sentinel_missing and cached is not None and isinstance(cached, dict):
        return dict(cached)
    if cached is None:
        return None

    getter = http_get_json or _http_get_json
    url = f"{_nominatim_base_url()}/reverse"
    params = {
        "format": "jsonv2",
        "lat": f"{lat_value:.6f}",
        "lon": f"{lon_value:.6f}",
        "addressdetails": "1",
        "zoom": "18",
    }

    _respect_rate_limit()
    try:
        payload = getter(
            url,
            params=params,
            timeout_seconds=_timeout_seconds(),
            user_agent=_user_agent(),
        )
    except Exception:
        _cache_set(cache_key, None)
        return None

    if not isinstance(payload, dict):
        _cache_set(cache_key, None)
        return None

    address_obj = payload.get("address") if isinstance(payload.get("address"), dict) else {}
    street = _safe_str(address_obj.get("road") or address_obj.get("pedestrian") or address_obj.get("residential"))
    house_number = _safe_str(address_obj.get("house_number"))
    plz = _safe_str(address_obj.get("postcode"))
    city = _safe_str(
        address_obj.get("city")
        or address_obj.get("town")
        or address_obj.get("village")
        or address_obj.get("municipality")
        or address_obj.get("hamlet"),
    )

    if not any([street, house_number, plz, city]):
        _cache_set(cache_key, None)
        return None

    confidence = _confidence_from_importance(payload.get("importance"), address_has_house_number=bool(house_number))

    result = {
        "street": street,
        "house_number": house_number,
        "plz": plz,
        "city": city,
        "confidence": confidence,
        "source": _SOURCE_LABEL,
        "data_class": _DATA_CLASS,
        "raw_label": _safe_str(payload.get("display_name")),
    }
    _cache_set(cache_key, result)
    return dict(result)


def clear_geocoding_cache_for_tests() -> None:
    global _last_request_monotonic
    with _cache_lock:
        _cache.clear()
    with _rate_lock:
        _last_request_monotonic = 0.0
