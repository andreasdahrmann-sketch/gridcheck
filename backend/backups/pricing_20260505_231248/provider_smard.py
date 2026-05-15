"""SMARD.de Provider fuer Day-Ahead Strompreise (Bundesnetzagentur, offiziell, frei)."""
import requests
import json
import time
from .cache import get_cached, set_cached
from .static_fallback import FALLBACK_STROMPREIS_EUR_MWH

SMARD_URL = "https://www.smard.de/app/chart_data/4169/DE/4169_DE_hour_{ts}.json"
SMARD_INDEX = "https://www.smard.de/app/chart_data/4169/DE/index_hour.json"

CACHE_KEY = "smard_dayahead_avg_30d"
CACHE_TTL = 86400  # 24h


def get_strompreis_eur_mwh(use_cache: bool = True) -> dict:
    """
    Liefert aktuellen Day-Ahead-Strompreis (30-Tage-Mittel) von SMARD.de.
    Returns: {"price_eur_mwh": float, "source": str, "timestamp": float}
    """
    if use_cache:
        cached = get_cached(CACHE_KEY, CACHE_TTL)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

    try:
        # Index der verfuegbaren Zeitstempel holen
        r = requests.get(SMARD_INDEX, timeout=8)
        r.raise_for_status()
        timestamps = r.json().get("timestamps", [])
        if not timestamps:
            raise ValueError("Keine Timestamps von SMARD")

        # Letzte verfuegbare Woche
        latest_ts = timestamps[-1]
        url = SMARD_URL.format(ts=latest_ts)
        r2 = requests.get(url, timeout=8)
        r2.raise_for_status()
        data = r2.json().get("series", [])

        # Mittelwert der letzten 30 Tage (max 720 Stunden)
        valid_prices = [v[1] for v in data if v[1] is not None]
        if not valid_prices:
            raise ValueError("Keine validen Preise")

        avg_eur_mwh = sum(valid_prices[-720:]) / len(valid_prices[-720:])

        result = {
            "price_eur_mwh": round(avg_eur_mwh, 2),
            "source": "SMARD.de (Bundesnetzagentur)",
            "timestamp": time.time(),
        }
        set_cached(CACHE_KEY, json.dumps(result))
        return result

    except Exception as e:
        return {
            "price_eur_mwh": FALLBACK_STROMPREIS_EUR_MWH,
            "source": f"Fallback (SMARD nicht erreichbar: {type(e).__name__})",
            "timestamp": time.time(),
        }
