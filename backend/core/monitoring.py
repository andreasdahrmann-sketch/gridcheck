from __future__ import annotations

import logging
import os

from core.config import settings

logger = logging.getLogger(__name__)
_initialized = False


def init_sentry() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
    except ImportError:
        logger.info("sentry_skip reason=sentry_sdk_not_installed")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.app_env,
        release=settings.app_version,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        integrations=[FastApiIntegration()],
    )
    logger.info("sentry_initialized environment=%s", settings.app_env)
