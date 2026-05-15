"""SQLite-Cache fuer Pricing-Daten mit TTL."""
import sqlite3
import time
import os
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "_cache"
CACHE_DIR.mkdir(exist_ok=True)
DB_PATH = CACHE_DIR / "pricing_cache.db"


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            ts REAL NOT NULL
        )
    """)
    return c


def get_cached(key: str, ttl_seconds: int = 86400):
    """Liefert Wert aus Cache oder None, wenn abgelaufen/fehlt."""
    try:
        c = _conn()
        cur = c.execute("SELECT value, ts FROM cache WHERE key=?", (key,))
        row = cur.fetchone()
        c.close()
        if not row:
            return None
        value, ts = row
        if (time.time() - ts) > ttl_seconds:
            return None
        return value
    except Exception:
        return None


def set_cached(key: str, value: str):
    """Speichert Wert im Cache."""
    try:
        c = _conn()
        c.execute(
            "INSERT OR REPLACE INTO cache (key, value, ts) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )
        c.commit()
        c.close()
    except Exception:
        pass
