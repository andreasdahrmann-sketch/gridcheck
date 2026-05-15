"""Dateibasierter JSON-Cache fuer Pricing-Daten mit TTL."""
import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "_cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "pricing_cache.json"


def _read_cache() -> dict[str, dict[str, object]]:
    if not CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_cache(data: dict[str, dict[str, object]]) -> None:
    CACHE_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")


def get_cached(key: str, ttl_seconds: int = 86400):
    """Liefert Wert aus Cache oder None, wenn abgelaufen/fehlt."""
    try:
        entry = _read_cache().get(key)
        if not isinstance(entry, dict):
            return None
        value = entry.get("value")
        ts = entry.get("ts")
        if not isinstance(value, str) or not isinstance(ts, (int, float)):
            return None
        if (time.time() - float(ts)) > ttl_seconds:
            return None
        return value
    except Exception:
        return None


def set_cached(key: str, value: str):
    """Speichert Wert im Cache."""
    try:
        data = _read_cache()
        data[key] = {"value": value, "ts": time.time()}
        _write_cache(data)
    except Exception:
        pass
