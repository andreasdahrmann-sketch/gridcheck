"""Unit-Tests fuer core.rate_limit (In-Memory-Backend)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from core import rate_limit as rl


def _reset() -> None:
    rl._MEM_BUCKETS.clear()
    rl._REDIS_CLIENT = None


@pytest.fixture(autouse=True)
def _isolated_buckets():
    _reset()
    yield
    _reset()


def test_allows_requests_under_limit():
    for _ in range(3):
        rl.enforce_rate_limit("unit:test", limit=3, window_seconds=60)


def test_blocks_when_limit_exceeded():
    for _ in range(2):
        rl.enforce_rate_limit("unit:block", limit=2, window_seconds=60)
    with pytest.raises(HTTPException) as exc:
        rl.enforce_rate_limit("unit:block", limit=2, window_seconds=60)
    assert exc.value.status_code == 429
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "RATE_LIMITED"


def test_scoped_rate_limit_requires_scope():
    with pytest.raises(ValueError):
        rl.enforce_scoped_rate_limit("scope-only", window_seconds=60)


def test_get_client_ip_from_forwarded_header():
    class _Client:
        host = "10.0.0.1"

    class _Request:
        headers = {"x-forwarded-for": "203.0.113.5, 10.0.0.1"}
        client = _Client()

    assert rl.get_client_ip(_Request()) == "203.0.113.5"
