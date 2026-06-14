"""Tests fuer core.logging_setup.

Wir testen:
- Renderer-Auswahl je nach APP_ENV (JSON in prod/staging, Console sonst)
- Secret-Masking-Processor maskiert password / authorization etc.
- nicht-sensible Felder bleiben unveraendert
"""
from __future__ import annotations

import json
import logging

import pytest

from core import logging_setup


@pytest.fixture(autouse=True)
def _reset_root_handlers():
    """Stellt sicher, dass jeder Test mit sauberem root-Logger startet."""
    root = logging.getLogger()
    saved = list(root.handlers)
    saved_level = root.level
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in saved:
        root.addHandler(handler)
    root.setLevel(saved_level)


def test_password_masking() -> None:
    event_in = {"event": "login_attempt", "password": "supersecret", "user_id": 42}
    out = logging_setup.mask_sensitive_processor(None, "info", dict(event_in))
    assert out["password"] == "***"
    assert out["user_id"] == 42
    assert out["event"] == "login_attempt"


def test_authorization_masking() -> None:
    event_in = {
        "event": "api_call",
        "authorization": "Bearer eyJhbGciOi...",
        "Authorization": "Basic abc",
        "api_key": "sk_test_xxx",
        "secret_value": "topsecret",
        "token": "ey...",
        "path": "/api/v1/projects",
    }
    out = logging_setup.mask_sensitive_processor(None, "info", dict(event_in))
    assert out["authorization"] == "***"
    assert out["Authorization"] == "***"
    assert out["api_key"] == "***"
    assert out["secret_value"] == "***"
    assert out["token"] == "***"
    assert out["path"] == "/api/v1/projects"


def test_masking_ignores_empty_values() -> None:
    event_in = {"password": "", "token": None, "user_id": 1}
    out = logging_setup.mask_sensitive_processor(None, "info", dict(event_in))
    # Leere / None-Werte bleiben unveraendert (kein irrefuehrendes '***').
    assert out["password"] == ""
    assert out["token"] is None
    assert out["user_id"] == 1


def test_json_renderer_in_prod(capsys: pytest.CaptureFixture[str]) -> None:
    logging_setup.configure_logging(app_env="prod", log_level="INFO")
    logger = logging_setup.get_logger("test.prod")
    logger.info("event_x", user_id=7, password="hidden")

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured, "Erwartete mindestens eine Logzeile"
    last = captured[-1]
    payload = json.loads(last)
    assert payload["event"] == "event_x"
    assert payload["user_id"] == 7
    assert payload["password"] == "***"
    assert payload["level"] == "info"
    assert "timestamp" in payload


def test_console_renderer_in_dev(capsys: pytest.CaptureFixture[str]) -> None:
    logging_setup.configure_logging(app_env="dev", log_level="DEBUG")
    logger = logging_setup.get_logger("test.dev")
    logger.info("event_dev", user_id=9, token="topsecret")

    out = capsys.readouterr().out
    # Console-Renderer ist kein JSON-Format.
    assert "event_dev" in out
    assert "user_id=9" in out
    assert "***" in out
    assert "topsecret" not in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out.strip().splitlines()[-1])


def test_log_level_filtering(capsys: pytest.CaptureFixture[str]) -> None:
    logging_setup.configure_logging(app_env="prod", log_level="WARNING")
    logger = logging_setup.get_logger("test.level")
    logger.debug("debug_event")
    logger.info("info_event")
    logger.warning("warn_event")

    captured = capsys.readouterr().out
    assert "warn_event" in captured
    assert "info_event" not in captured
    assert "debug_event" not in captured
