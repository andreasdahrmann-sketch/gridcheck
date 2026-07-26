"""Unit-Tests fuer core.rate_limit (In-Memory- und Redis-Backend)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from core import rate_limit as rl


class _FakeRedis:
    """Minimal Redis stand-in for INCR/TTL/EXPIRE rate-limit behaviour."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.counts[key] = int(self.counts.get(key, 0)) + 1
        return self.counts[key]

    def ttl(self, key: str) -> int:
        if key not in self.counts:
            return -2
        if key not in self.ttls:
            return -1
        return int(self.ttls[key])

    def expire(self, key: str, seconds: int) -> bool:
        if key not in self.counts:
            return False
        self.ttls[key] = int(seconds)
        return True


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


def test_redis_heals_missing_ttl_after_incr_without_expire(monkeypatch):
    """Crash/network gap after INCR must not permanently lock a bucket."""
    fake = _FakeRedis()
    monkeypatch.setattr(rl, "_get_redis_client", lambda: fake)

    # Simulate aborted first hit: counter exists, TTL was never set.
    fake.counts["dsgvo:export:user:42"] = 1
    assert fake.ttl("dsgvo:export:user:42") == -1

    # Next request must restore EXPIRE and still allow limit=2 (current becomes 2).
    rl.enforce_rate_limit("dsgvo:export:user:42", limit=2, window_seconds=3600)
    assert fake.counts["dsgvo:export:user:42"] == 2
    assert fake.ttl("dsgvo:export:user:42") == 3600


def test_redis_sets_expire_on_first_incr(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(rl, "_get_redis_client", lambda: fake)

    rl.enforce_rate_limit("auth:login:user@example.com", limit=10, window_seconds=300)
    assert fake.counts["auth:login:user@example.com"] == 1
    assert fake.ttl("auth:login:user@example.com") == 300


def test_redis_blocks_when_limit_exceeded_but_keeps_ttl(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(rl, "_get_redis_client", lambda: fake)

    rl.enforce_rate_limit("unit:redis-block", limit=1, window_seconds=86_400)
    with pytest.raises(HTTPException) as exc:
        rl.enforce_rate_limit("unit:redis-block", limit=1, window_seconds=86_400)
    assert exc.value.status_code == 429
    assert fake.ttl("unit:redis-block") == 86_400
