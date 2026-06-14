"""Sentry-Initialisierung (fail-soft).

- Wenn `SENTRY_DSN` gesetzt: initialisiere sentry-sdk mit FastAPI-Integration.
- Wenn nicht gesetzt: strukturierte Warn-Logzeile, KEIN Crash.
- `capture_exception()` ist no-op, solange Sentry nicht initialisiert ist,
  damit Aufrufer keine if-Bedingungen brauchen.
"""
from __future__ import annotations

import os
from typing import Any

from core.config import settings
from core.logging_setup import get_logger

logger = get_logger("gridcheck.monitoring")

_initialized = False
_sentry_module: Any = None


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip())


def init_sentry() -> None:
    """Initialisiert Sentry, falls SENTRY_DSN gesetzt ist.

    Fail-soft: Bei fehlender DSN oder fehlendem sentry-sdk wird gewarnt,
    aber keine Exception geworfen. Mehrfacher Aufruf ist idempotent.
    """
    global _initialized, _sentry_module
    if _initialized:
        return

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.warning(
            "sentry_skip",
            reason="dsn_not_set",
            hint="SENTRY_DSN setzen, um Error-Tracking zu aktivieren.",
            app_env=settings.app_env,
        )
        _initialized = True
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning(
            "sentry_skip",
            reason="sentry_sdk_not_installed",
            hint="pip install -r requirements.txt im backend/-Ordner.",
        )
        _initialized = True
        return

    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0"))

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.app_env,
        release=settings.app_version,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        send_default_pii=False,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
    )
    _sentry_module = sentry_sdk
    _initialized = True
    logger.info(
        "sentry_initialized",
        environment=settings.app_env,
        release=settings.app_version,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
    )


def capture_exception(exc: BaseException) -> None:
    """No-op, solange Sentry nicht initialisiert ist. Sonst Forward an Sentry."""
    if _sentry_module is None:
        return
    try:
        _sentry_module.capture_exception(exc)
    except Exception:  # noqa: BLE001 - Telemetrie darf den Aufrufer nie kippen.
        logger.warning("sentry_capture_failed", exc_type=type(exc).__name__)


def is_initialized() -> bool:
    """Hilfsfunktion fuer Tests."""
    return _sentry_module is not None


def _reset_for_tests() -> None:
    """Nur fuer Tests: Modulstatus zuruecksetzen."""
    global _initialized, _sentry_module
    _initialized = False
    _sentry_module = None
