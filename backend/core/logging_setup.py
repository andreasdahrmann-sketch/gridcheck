"""Zentrale Logging-Konfiguration (structlog).

- JSON-Renderer in staging/prod (maschinell auswertbar, z. B. fuer Loki/CloudWatch).
- ConsoleRenderer in dev/test (entwicklerfreundlich).
- Maskierung von Secret-Feldern (password, token, secret, authorization, api_key)
  als zusaetzliche Defense-in-Depth: niemals Secrets in Logs.
- stdlib `logging` (FastAPI, uvicorn, sqlalchemy) wird via ProcessorFormatter an
  dieselbe Renderer-Chain gebunden, damit alle Logs konsistent durchlaufen.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


# Felder, deren Werte beim Loggen immer maskiert werden.
# Match: Teilstring im Key (case-insensitive). "Authorization" -> match,
# "authorization_header" -> match, "auth_method" -> NICHT match (zu generisch).
_SENSITIVE_KEY_SUBSTRINGS: tuple[str, ...] = (
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
)

_MASK = "***"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in _SENSITIVE_KEY_SUBSTRINGS)


def mask_sensitive_processor(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog-Processor: maskiert Werte zu sensiblen Keys."""
    for key in list(event_dict.keys()):
        if _is_sensitive_key(key) and event_dict.get(key) not in (None, ""):
            event_dict[key] = _MASK
    return event_dict


def _resolve_renderer(app_env: str) -> Any:
    if app_env in {"staging", "prod", "production"}:
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer(colors=False)


def _resolve_log_level(log_level: str) -> int:
    level = (log_level or "INFO").strip().upper()
    return getattr(logging, level, logging.INFO)


def configure_logging(*, app_env: str, log_level: str) -> None:
    """Initialisiert structlog + stdlib logging.

    Idempotent: mehrfacher Aufruf ist erlaubt (z. B. Tests).
    """
    level = _resolve_log_level(log_level)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        mask_sensitive_processor,
    ]

    renderer = _resolve_renderer(app_env)

    # structlog-Loggers reichen das event_dict via wrap_for_formatter an stdlib
    # weiter; die finale Renderchain (renderer) laeuft im ProcessorFormatter.
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    for existing in list(root_logger.handlers):
        root_logger.removeHandler(existing)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Noise reduzieren: uvicorn-access auf WARN, sonst flutet jeder Health-Check.
    logging.getLogger("uvicorn.access").setLevel(max(level, logging.WARNING))


def get_logger(name: str | None = None) -> Any:
    """Convenience-Wrapper, damit Module nicht direkt von structlog importieren muessen."""
    return structlog.get_logger(name) if name else structlog.get_logger()
