from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from fastapi import HTTPException, Request

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


def _sanitize_bucket_part(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    sanitized = "".join(ch if ch.isalnum() or ch in {".", "-", "_", ":"} else "_" for ch in text)
    return sanitized[:160] or "unknown"


def _format_window(window_seconds: int) -> str:
    if window_seconds % 3600 == 0 and window_seconds >= 3600:
        hours = window_seconds // 3600
        return "1 Stunde" if hours == 1 else f"{hours} Stunden"
    if window_seconds % 60 == 0 and window_seconds >= 60:
        minutes = window_seconds // 60
        return "1 Minute" if minutes == 1 else f"{minutes} Minuten"
    return f"{window_seconds} Sekunden"


def _rate_limit_detail(*, window_seconds: int, message: str | None = None, hint: str | None = None) -> dict[str, str]:
    return {
        "code": "RATE_LIMITED",
        "message": message or "Zu viele Anfragen",
        "hint": hint or f"Bitte in etwa {_format_window(window_seconds)} erneut versuchen.",
    }


def get_client_ip(request: Request | None) -> str:
    if request is None:
        return "unknown"
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for.strip():
        return _sanitize_bucket_part(forwarded_for.split(",")[0])
    if request.client and request.client.host:
        return _sanitize_bucket_part(request.client.host)
    return "unknown"


def enforce_rate_limit(
    bucket_key: str,
    *,
    limit: int,
    window_seconds: int,
    message: str | None = None,
    hint: str | None = None,
) -> None:
    detail = _rate_limit_detail(window_seconds=window_seconds, message=message, hint=hint)
    redis_client = _get_redis_client()
    if redis_client:
        current = redis_client.incr(bucket_key)
        if current == 1:
            redis_client.expire(bucket_key, window_seconds)
        if current > limit:
            log_security_event("rate_limited", bucket=bucket_key, limit=limit, window_seconds=window_seconds, backend="redis")
            raise HTTPException(status_code=429, detail=detail)
        return

    now = time.time()
    bucket = _MEM_BUCKETS[bucket_key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        log_security_event("rate_limited", bucket=bucket_key, limit=limit, window_seconds=window_seconds, backend="memory")
        raise HTTPException(status_code=429, detail=detail)
    bucket.append(now)


def enforce_scoped_rate_limit(
    scope: str,
    *,
    window_seconds: int,
    request: Request | None = None,
    current_user: Any | None = None,
    user_limit: int | None = None,
    ip_limit: int | None = None,
    message: str | None = None,
    hint: str | None = None,
) -> None:
    if user_limit is None and ip_limit is None:
        raise ValueError("At least one rate-limit scope must be configured.")

    scope_key = _sanitize_bucket_part(scope)
    user_id = getattr(current_user, "id", None)
    if user_limit is not None and user_id is not None:
        enforce_rate_limit(
            f"{scope_key}:user:{_sanitize_bucket_part(user_id)}",
            limit=user_limit,
            window_seconds=window_seconds,
            message=message,
            hint=hint,
        )

    if ip_limit is not None:
        enforce_rate_limit(
            f"{scope_key}:ip:{get_client_ip(request)}",
            limit=ip_limit,
            window_seconds=window_seconds,
            message=message,
            hint=hint,
        )
