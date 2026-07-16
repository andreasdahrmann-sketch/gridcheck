"""Tests fuer core.monitoring (Sentry Init, fail-soft).

KEIN realer Sentry-Call: wir monkeypatchen sentry_sdk.init.
"""
from __future__ import annotations

import sys
import types

import pytest

from core import monitoring


@pytest.fixture(autouse=True)
def _reset_monitoring_state():
    monitoring._reset_for_tests()
    yield
    monitoring._reset_for_tests()


def _install_fake_sentry(monkeypatch: pytest.MonkeyPatch, init_calls: list[dict]) -> types.ModuleType:
    """Installiert ein Fake-sentry_sdk + Integration-Module in sys.modules."""

    fake_sentry = types.ModuleType("sentry_sdk")

    def fake_init(**kwargs):  # noqa: ANN003
        init_calls.append(kwargs)

    captured: list[BaseException] = []

    def fake_capture(exc):  # noqa: ANN001
        captured.append(exc)

    fake_sentry.init = fake_init  # type: ignore[attr-defined]
    fake_sentry.capture_exception = fake_capture  # type: ignore[attr-defined]
    fake_sentry._captured = captured  # type: ignore[attr-defined]

    integrations_pkg = types.ModuleType("sentry_sdk.integrations")
    fastapi_mod = types.ModuleType("sentry_sdk.integrations.fastapi")
    starlette_mod = types.ModuleType("sentry_sdk.integrations.starlette")

    class _FastApiIntegration:
        def __init__(self, *args, **kwargs):
            pass

    class _StarletteIntegration:
        def __init__(self, *args, **kwargs):
            pass

    fastapi_mod.FastApiIntegration = _FastApiIntegration  # type: ignore[attr-defined]
    starlette_mod.StarletteIntegration = _StarletteIntegration  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations", integrations_pkg)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.starlette", starlette_mod)
    return fake_sentry


def test_init_skipped_when_dsn_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monitoring.init_sentry()
    assert monitoring.is_initialized() is False


def test_init_called_when_dsn_set(monkeypatch: pytest.MonkeyPatch) -> None:
    init_calls: list[dict] = []
    _install_fake_sentry(monkeypatch, init_calls)

    monkeypatch.setenv("SENTRY_DSN", "https://public@sentry.example/1")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")
    monkeypatch.setenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")

    monitoring.init_sentry()

    assert monitoring.is_initialized() is True
    assert len(init_calls) == 1
    kwargs = init_calls[0]
    assert kwargs["dsn"] == "https://public@sentry.example/1"
    assert kwargs["traces_sample_rate"] == 0.25
    assert kwargs["profiles_sample_rate"] == 0.0
    assert kwargs["send_default_pii"] is False
    assert "environment" in kwargs
    assert "release" in kwargs
    assert "integrations" in kwargs and kwargs["integrations"]


@pytest.mark.parametrize(
    ("traces_value", "profiles_value"),
    [
        ("", ""),
        ("not-a-number", "2.0"),
    ],
)
def test_invalid_sample_rates_fall_back_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
    traces_value: str,
    profiles_value: str,
) -> None:
    init_calls: list[dict] = []
    _install_fake_sentry(monkeypatch, init_calls)
    monkeypatch.setenv("SENTRY_DSN", "https://public@sentry.example/1")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", traces_value)
    monkeypatch.setenv("SENTRY_PROFILES_SAMPLE_RATE", profiles_value)

    monitoring.init_sentry()

    assert len(init_calls) == 1
    assert init_calls[0]["traces_sample_rate"] == 0.1
    assert init_calls[0]["profiles_sample_rate"] == 0.0
    assert monitoring.is_initialized() is True


def test_sentry_sdk_init_failure_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    init_calls: list[dict] = []
    fake_sentry = _install_fake_sentry(monkeypatch, init_calls)
    monkeypatch.setenv("SENTRY_DSN", "invalid-dsn")

    def fail_init(**kwargs):  # noqa: ANN003
        raise ValueError("invalid DSN")

    fake_sentry.init = fail_init  # type: ignore[attr-defined]

    monitoring.init_sentry()

    assert monitoring.is_initialized() is False


def test_init_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    init_calls: list[dict] = []
    _install_fake_sentry(monkeypatch, init_calls)
    monkeypatch.setenv("SENTRY_DSN", "https://public@sentry.example/1")

    monitoring.init_sentry()
    monitoring.init_sentry()
    monitoring.init_sentry()

    assert len(init_calls) == 1


def test_capture_exception_is_noop_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monitoring.init_sentry()
    # Darf nicht crashen, auch wenn Sentry nicht initialisiert ist.
    monitoring.capture_exception(RuntimeError("boom"))


def test_capture_exception_forwards_when_initialized(monkeypatch: pytest.MonkeyPatch) -> None:
    init_calls: list[dict] = []
    fake_sentry = _install_fake_sentry(monkeypatch, init_calls)
    monkeypatch.setenv("SENTRY_DSN", "https://public@sentry.example/1")
    monitoring.init_sentry()

    err = RuntimeError("boom")
    monitoring.capture_exception(err)
    assert fake_sentry._captured == [err]  # type: ignore[attr-defined]
