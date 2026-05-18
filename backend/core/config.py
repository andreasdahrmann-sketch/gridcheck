from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_postgres_url(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered.startswith("postgresql://") or lowered.startswith("postgresql+") or lowered.startswith("postgres://")


def normalize_database_url(value: str) -> str:
    """Railway/Heroku liefern oft postgres://; SQLAlchemy 2 erwartet postgresql://."""
    trimmed = value.strip()
    if trimmed.lower().startswith("postgres://"):
        return "postgresql://" + trimmed[len("postgres://") :]
    return trimmed


def _validate_prefixed_value(name: str, value: str | None, prefixes: tuple[str, ...]) -> None:
    if not value:
        return
    if any(value.startswith(prefix) for prefix in prefixes):
        return
    expected = " oder ".join(prefixes)
    raise RuntimeError(f"{name} muss mit {expected} beginnen.")


def _validate_http_url(name: str, value: str | None, *, allow_localhost: bool) -> None:
    if not value:
        return
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(f"{name} muss eine absolute http(s)-URL sein.")
    host = (parsed.hostname or "").strip().lower()
    if not allow_localhost and host in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError(f"{name} darf in staging/prod nicht auf localhost zeigen.")


def _validate_regex(name: str, value: str | None) -> None:
    if not value:
        return
    try:
        re.compile(value)
    except re.error as exc:
        raise RuntimeError(f"{name} muss ein gueltiger Regex sein.") from exc


def _validate_stripe_settings(
    *,
    app_env: str,
    stripe_secret_key: str | None,
    stripe_publishable_key: str | None,
    stripe_webhook_secret: str | None,
    stripe_price_basic_id: str | None,
    stripe_price_premium_id: str | None,
    stripe_price_professional_id: str | None,
    stripe_price_pro_license_id: str | None,
    stripe_price_express_id: str | None,
    stripe_checkout_success_url: str | None,
    stripe_checkout_cancel_url: str | None,
    stripe_portal_return_url: str | None,
) -> None:
    stripe_values = [
        stripe_secret_key,
        stripe_publishable_key,
        stripe_webhook_secret,
        stripe_price_basic_id,
        stripe_price_premium_id,
        stripe_price_professional_id,
        stripe_price_pro_license_id,
        stripe_price_express_id,
        stripe_checkout_success_url,
        stripe_checkout_cancel_url,
        stripe_portal_return_url,
    ]
    if not any(stripe_values):
        return

    required = {
        "STRIPE_SECRET_KEY": stripe_secret_key,
        "STRIPE_WEBHOOK_SECRET": stripe_webhook_secret,
        "STRIPE_PRICE_BASIC_ID": stripe_price_basic_id,
        "STRIPE_PRICE_PREMIUM_ID": stripe_price_premium_id,
        "STRIPE_PRICE_PROFESSIONAL_ID": stripe_price_professional_id,
        "STRIPE_PRICE_PRO_LICENSE_ID": stripe_price_pro_license_id,
        "STRIPE_CHECKOUT_SUCCESS_URL": stripe_checkout_success_url,
        "STRIPE_CHECKOUT_CANCEL_URL": stripe_checkout_cancel_url,
        "STRIPE_PORTAL_RETURN_URL": stripe_portal_return_url,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(f"Stripe ist nur teilweise konfiguriert. Fehlende Pflichtvariablen: {missing_list}")

    allow_localhost = app_env in {"dev", "test"}
    _validate_http_url("STRIPE_CHECKOUT_SUCCESS_URL", stripe_checkout_success_url, allow_localhost=allow_localhost)
    _validate_http_url("STRIPE_CHECKOUT_CANCEL_URL", stripe_checkout_cancel_url, allow_localhost=allow_localhost)
    _validate_http_url("STRIPE_PORTAL_RETURN_URL", stripe_portal_return_url, allow_localhost=allow_localhost)

    _validate_prefixed_value("STRIPE_WEBHOOK_SECRET", stripe_webhook_secret, ("whsec_",))
    _validate_prefixed_value("STRIPE_PRICE_BASIC_ID", stripe_price_basic_id, ("price_",))
    _validate_prefixed_value("STRIPE_PRICE_PREMIUM_ID", stripe_price_premium_id, ("price_",))
    _validate_prefixed_value("STRIPE_PRICE_PROFESSIONAL_ID", stripe_price_professional_id, ("price_",))
    _validate_prefixed_value("STRIPE_PRICE_PRO_LICENSE_ID", stripe_price_pro_license_id, ("price_",))
    _validate_prefixed_value("STRIPE_PRICE_EXPRESS_ID", stripe_price_express_id, ("price_",))

    if app_env == "staging":
        _validate_prefixed_value("STRIPE_SECRET_KEY", stripe_secret_key, ("sk_test_",))
        _validate_prefixed_value("STRIPE_PUBLISHABLE_KEY", stripe_publishable_key, ("pk_test_",))
    elif app_env in {"prod", "production"}:
        _validate_prefixed_value("STRIPE_SECRET_KEY", stripe_secret_key, ("sk_live_",))
        _validate_prefixed_value("STRIPE_PUBLISHABLE_KEY", stripe_publishable_key, ("pk_live_",))
    else:
        _validate_prefixed_value("STRIPE_SECRET_KEY", stripe_secret_key, ("sk_test_", "sk_live_"))
        _validate_prefixed_value("STRIPE_PUBLISHABLE_KEY", stripe_publishable_key, ("pk_test_", "pk_live_"))


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_version: str
    database_url: str
    cors_origins: list[str]
    cors_origin_regex: str | None
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
    free_checks_limit: int
    stripe_secret_key: str | None
    stripe_publishable_key: str | None
    stripe_webhook_secret: str | None
    stripe_price_id: str | None
    stripe_price_basic_id: str | None
    stripe_price_premium_id: str | None
    stripe_price_professional_id: str | None
    stripe_price_pro_license_id: str | None
    stripe_price_express_id: str | None
    stripe_checkout_success_url: str | None
    stripe_checkout_cancel_url: str | None
    stripe_portal_return_url: str | None


def load_settings() -> Settings:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    app_env = os.getenv("APP_ENV", "dev").strip().lower() or "dev"
    app_version = os.getenv("APP_VERSION", "dev").strip() or "dev"
    database_url = normalize_database_url(os.getenv("DATABASE_URL", "").strip())
    cors_csv = os.getenv("CORS_ORIGINS", "").strip()
    cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None
    log_level = os.getenv("LOG_LEVEL", "INFO").strip() or "INFO"
    jwt_secret = os.getenv("JWT_SECRET")
    jwt_refresh_secret = os.getenv("JWT_REFRESH_SECRET")
    trusted_hosts_csv = os.getenv("TRUSTED_HOSTS", "").strip()
    redis_url = os.getenv("REDIS_URL", "").strip() or None
    auth_access_cookie = os.getenv("AUTH_ACCESS_COOKIE", "gridcheck_access")
    auth_refresh_cookie = os.getenv("AUTH_REFRESH_COOKIE", "gridcheck_refresh")
    auth_csrf_cookie = os.getenv("AUTH_CSRF_COOKIE", "gridcheck_csrf")
    free_checks_limit_raw = os.getenv("FREE_CHECKS_LIMIT", "3").strip() or "3"
    auto_create_schema_env = os.getenv("AUTO_CREATE_SCHEMA")
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip() or None
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip() or None
    stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip() or None
    stripe_price_id = os.getenv("STRIPE_PRICE_ID", "").strip() or None
    stripe_price_basic_id = os.getenv("STRIPE_PRICE_BASIC_ID", "").strip() or None
    stripe_price_premium_id = os.getenv("STRIPE_PRICE_PREMIUM_ID", "").strip() or None
    stripe_price_professional_id = os.getenv("STRIPE_PRICE_PROFESSIONAL_ID", "").strip() or None
    stripe_price_pro_license_id = os.getenv("STRIPE_PRICE_PRO_LICENSE_ID", "").strip() or stripe_price_id
    stripe_price_express_id = os.getenv("STRIPE_PRICE_EXPRESS_ID", "").strip() or None
    stripe_checkout_success_url = os.getenv("STRIPE_CHECKOUT_SUCCESS_URL", "").strip() or None
    stripe_checkout_cancel_url = os.getenv("STRIPE_CHECKOUT_CANCEL_URL", "").strip() or None
    stripe_portal_return_url = os.getenv("STRIPE_PORTAL_RETURN_URL", "").strip() or None

    try:
        free_checks_limit = max(0, int(free_checks_limit_raw))
    except ValueError as exc:
        raise RuntimeError("FREE_CHECKS_LIMIT muss eine ganze Zahl >= 0 sein.") from exc

    auto_create_schema = False
    if auto_create_schema_env is not None and auto_create_schema_env.strip() != "":
        auto_create_schema = auto_create_schema_env.strip().lower() in {"1", "true", "yes", "on"}
        if auto_create_schema:
            raise RuntimeError(
                "AUTO_CREATE_SCHEMA=true ist nicht mehr zulaessig. "
                "Schema-Aenderungen duerfen ausschliesslich via Alembic-Migration erfolgen."
            )
    # Explizites Override gewinnt. Sonst: in staging/prod/prod-like standardmaessig aus (Migration zu /api/v1).
    legacy_env = os.getenv("ENABLE_LEGACY_ROUTES")
    if legacy_env is not None and legacy_env.strip() != "":
        enable_legacy_routes = legacy_env.strip().lower() in {"1", "true", "yes", "on"}
    else:
        enable_legacy_routes = app_env not in {"staging", "prod", "production"}

    if not database_url:
        raise RuntimeError("Missing required env var: DATABASE_URL (PostgreSQL erforderlich)")
    if not _is_postgres_url(database_url):
        raise RuntimeError("DATABASE_URL muss auf PostgreSQL zeigen. SQLite und andere Engines sind nicht unterstuetzt.")

    # Fail-fast in non-dev environments.
    if app_env in {"staging", "prod", "production"}:
        if not cors_csv and not cors_origin_regex:
            raise RuntimeError("Missing required env var: CORS_ORIGINS oder CORS_ORIGIN_REGEX")
        if not jwt_secret:
            raise RuntimeError("Missing required env var: JWT_SECRET")
        if not jwt_refresh_secret:
            raise RuntimeError("Missing required env var: JWT_REFRESH_SECRET")

    _validate_regex("CORS_ORIGIN_REGEX", cors_origin_regex)

    _validate_stripe_settings(
        app_env=app_env,
        stripe_secret_key=stripe_secret_key,
        stripe_publishable_key=stripe_publishable_key,
        stripe_webhook_secret=stripe_webhook_secret,
        stripe_price_basic_id=stripe_price_basic_id,
        stripe_price_premium_id=stripe_price_premium_id,
        stripe_price_professional_id=stripe_price_professional_id,
        stripe_price_pro_license_id=stripe_price_pro_license_id,
        stripe_price_express_id=stripe_price_express_id,
        stripe_checkout_success_url=stripe_checkout_success_url,
        stripe_checkout_cancel_url=stripe_checkout_cancel_url,
        stripe_portal_return_url=stripe_portal_return_url,
    )

    if cors_csv:
        cors_origins = _split_csv(cors_csv)
    elif app_env in {"dev", "test"}:
        cors_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
        ]
    else:
        cors_origins = []

    return Settings(
        app_env=app_env,
        app_version=app_version,
        database_url=database_url,
        cors_origins=cors_origins,
        cors_origin_regex=cors_origin_regex,
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
        free_checks_limit=free_checks_limit,
        stripe_secret_key=stripe_secret_key,
        stripe_publishable_key=stripe_publishable_key,
        stripe_webhook_secret=stripe_webhook_secret,
        stripe_price_id=stripe_price_id,
        stripe_price_basic_id=stripe_price_basic_id,
        stripe_price_premium_id=stripe_price_premium_id,
        stripe_price_professional_id=stripe_price_professional_id,
        stripe_price_pro_license_id=stripe_price_pro_license_id,
        stripe_price_express_id=stripe_price_express_id,
        stripe_checkout_success_url=stripe_checkout_success_url,
        stripe_checkout_cancel_url=stripe_checkout_cancel_url,
        stripe_portal_return_url=stripe_portal_return_url,
    )


settings = load_settings()
