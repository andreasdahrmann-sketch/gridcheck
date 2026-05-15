from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException

from core.config import settings
from core.security_log import log_security_event

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

_MEM_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_REDIS_CLIENT = None


def _get_redis_client():
    global _REDIS_CLIENT
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT
    if not settings.redis_url or redis is None:
        return None
    _REDIS_CLIENT = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _REDIS_CLIENT


def enforce_rate_limit(bucket_key: str, *, limit: int, window_seconds: int) -> None:
    redis_client = _get_redis_client()
    if redis_client:
        current = redis_client.incr(bucket_key)
        if current == 1:
            redis_client.expire(bucket_key, window_seconds)
        if current > limit:
            log_security_event("rate_limited", bucket=bucket_key, limit=limit, window_seconds=window_seconds, backend="redis")
            raise HTTPException(
                status_code=429,
                detail={"code": "RATE_LIMITED", "message": "Zu viele Anfragen", "hint": "Bitte spaeter erneut versuchen."},
            )
        return

    now = time.time()
    bucket = _MEM_BUCKETS[bucket_key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        log_security_event("rate_limited", bucket=bucket_key, limit=limit, window_seconds=window_seconds, backend="memory")
        raise HTTPException(
            status_code=429,
            detail={"code": "RATE_LIMITED", "message": "Zu viele Anfragen", "hint": "Bitte spaeter erneut versuchen."},
        )
    bucket.append(now)
