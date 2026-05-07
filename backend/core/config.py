from __future__ import annotations

import os
from dataclasses import dataclass


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_version: str
    database_url: str
    cors_origins: list[str]
    log_level: str
    jwt_secret: str | None
    jwt_refresh_secret: str | None
    enable_legacy_routes: bool
    trusted_hosts: list[str]
    redis_url: str | None
    auth_access_cookie: str
    auth_refresh_cookie: str
    auth_csrf_cookie: str
    auto_create_schema: bool


def load_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "dev").strip().lower() or "dev"
    app_version = os.getenv("APP_VERSION", "dev").strip() or "dev"
    database_url = os.getenv("DATABASE_URL", "").strip()
    cors_csv = os.getenv("CORS_ORIGINS", "").strip()
    log_level = os.getenv("LOG_LEVEL", "INFO").strip() or "INFO"
    jwt_secret = os.getenv("JWT_SECRET")
    jwt_refresh_secret = os.getenv("JWT_REFRESH_SECRET")
    trusted_hosts_csv = os.getenv("TRUSTED_HOSTS", "").strip()
    redis_url = os.getenv("REDIS_URL", "").strip() or None
    auth_access_cookie = os.getenv("AUTH_ACCESS_COOKIE", "gridcheck_access")
    auth_refresh_cookie = os.getenv("AUTH_REFRESH_COOKIE", "gridcheck_refresh")
    auth_csrf_cookie = os.getenv("AUTH_CSRF_COOKIE", "gridcheck_csrf")
    auto_create_schema_env = os.getenv("AUTO_CREATE_SCHEMA")
    if auto_create_schema_env is None or auto_create_schema_env.strip() == "":
        auto_create_schema = app_env in {"dev", "test"}
    else:
        auto_create_schema = auto_create_schema_env.strip().lower() in {"1", "true", "yes", "on"}
    # Explizites Override gewinnt. Sonst: in staging/prod/prod-like standardmaessig aus (Migration zu /api/v1).
    legacy_env = os.getenv("ENABLE_LEGACY_ROUTES")
    if legacy_env is not None and legacy_env.strip() != "":
        enable_legacy_routes = legacy_env.strip().lower() in {"1", "true", "yes", "on"}
    else:
        enable_legacy_routes = app_env not in {"staging", "prod", "production"}

    # Fail-fast in non-dev environments.
    if app_env in {"staging", "prod", "production"}:
        if not database_url:
            raise RuntimeError("Missing required env var: DATABASE_URL")
        if not cors_csv:
            raise RuntimeError("Missing required env var: CORS_ORIGINS")
        if not jwt_secret:
            raise RuntimeError("Missing required env var: JWT_SECRET")
        if not jwt_refresh_secret:
            raise RuntimeError("Missing required env var: JWT_REFRESH_SECRET")

    # Local/test-safe fallback; production must pass explicit DATABASE_URL.
    if not database_url:
        database_url = "sqlite:///./gridcheck.db"

    cors_origins = _split_csv(cors_csv) if cors_csv else [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    return Settings(
        app_env=app_env,
        app_version=app_version,
        database_url=database_url,
        cors_origins=cors_origins,
        log_level=log_level,
        jwt_secret=jwt_secret,
        jwt_refresh_secret=jwt_refresh_secret,
        enable_legacy_routes=enable_legacy_routes,
        trusted_hosts=_split_csv(trusted_hosts_csv) if trusted_hosts_csv else ["localhost", "127.0.0.1"],
        redis_url=redis_url,
        auth_access_cookie=auth_access_cookie,
        auth_refresh_cookie=auth_refresh_cookie,
        auth_csrf_cookie=auth_csrf_cookie,
        auto_create_schema=auto_create_schema,
    )


settings = load_settings()
