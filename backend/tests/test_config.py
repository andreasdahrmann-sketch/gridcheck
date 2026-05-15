from __future__ import annotations

import pytest

from core import config as config_module


BASE_KEYS = [
    "APP_ENV",
    "APP_VERSION",
    "DATABASE_URL",
    "AUTO_CREATE_SCHEMA",
    "CORS_ORIGINS",
    "CORS_ORIGIN_REGEX",
    "JWT_SECRET",
    "JWT_REFRESH_SECRET",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_ID",
    "STRIPE_PRICE_BASIC_ID",
    "STRIPE_PRICE_PREMIUM_ID",
    "STRIPE_PRICE_PROFESSIONAL_ID",
    "STRIPE_PRICE_PRO_LICENSE_ID",
    "STRIPE_PRICE_EXPRESS_ID",
    "STRIPE_CHECKOUT_SUCCESS_URL",
    "STRIPE_CHECKOUT_CANCEL_URL",
    "STRIPE_PORTAL_RETURN_URL",
]


def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in BASE_KEYS:
        monkeypatch.delenv(key, raising=False)


def _set_base_env(monkeypatch: pytest.MonkeyPatch, *, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("APP_VERSION", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://gridcheck:gridcheck_dev_2026@localhost:5433/gridcheck")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.gridcheck.de")
    monkeypatch.setenv("JWT_SECRET", "pytest-gridcheck-access-secret-32-chars")
    monkeypatch.setenv("JWT_REFRESH_SECRET", "pytest-gridcheck-refresh-secret-32")


def _set_complete_stripe_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    secret_key: str,
    publishable_key: str,
    checkout_success_url: str,
    checkout_cancel_url: str,
    portal_return_url: str,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", secret_key)
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", publishable_key)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_legacy_fallback")
    monkeypatch.setenv("STRIPE_PRICE_BASIC_ID", "price_basic_123")
    monkeypatch.setenv("STRIPE_PRICE_PREMIUM_ID", "price_premium_123")
    monkeypatch.setenv("STRIPE_PRICE_PROFESSIONAL_ID", "price_professional_123")
    monkeypatch.setenv("STRIPE_PRICE_PRO_LICENSE_ID", "price_pro_license_123")
    monkeypatch.setenv("STRIPE_PRICE_EXPRESS_ID", "price_express_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_SUCCESS_URL", checkout_success_url)
    monkeypatch.setenv("STRIPE_CHECKOUT_CANCEL_URL", checkout_cancel_url)
    monkeypatch.setenv("STRIPE_PORTAL_RETURN_URL", portal_return_url)


def test_load_settings_rejects_partial_stripe_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    _set_base_env(monkeypatch, app_env="dev")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_partial")

    with pytest.raises(RuntimeError, match="Stripe ist nur teilweise konfiguriert"):
        config_module.load_settings()


def test_load_settings_rejects_auto_create_schema_true(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    _set_base_env(monkeypatch, app_env="dev")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "true")

    with pytest.raises(RuntimeError, match="AUTO_CREATE_SCHEMA=true ist nicht mehr zulaessig"):
        config_module.load_settings()


def test_load_settings_requires_testmode_keys_in_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    _set_base_env(monkeypatch, app_env="staging")
    _set_complete_stripe_env(
        monkeypatch,
        secret_key="sk_live_not_allowed",
        publishable_key="pk_live_not_allowed",
        checkout_success_url="https://staging.gridcheck.de/settings?billing=success",
        checkout_cancel_url="https://staging.gridcheck.de/settings?billing=cancel",
        portal_return_url="https://staging.gridcheck.de/settings",
    )

    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY muss mit sk_test_ beginnen"):
        config_module.load_settings()


def test_load_settings_rejects_localhost_return_urls_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    _set_base_env(monkeypatch, app_env="prod")
    _set_complete_stripe_env(
        monkeypatch,
        secret_key="sk_live_prod_123",
        publishable_key="pk_live_prod_123",
        checkout_success_url="http://localhost:3000/settings?billing=success",
        checkout_cancel_url="https://app.gridcheck.de/settings?billing=cancel",
        portal_return_url="https://app.gridcheck.de/settings",
    )

    with pytest.raises(RuntimeError, match="STRIPE_CHECKOUT_SUCCESS_URL darf in staging/prod nicht auf localhost zeigen"):
        config_module.load_settings()


def test_load_settings_accepts_complete_staging_testmode_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    _set_base_env(monkeypatch, app_env="staging")
    _set_complete_stripe_env(
        monkeypatch,
        secret_key="sk_test_staging_123",
        publishable_key="pk_test_staging_123",
        checkout_success_url="https://staging.gridcheck.de/settings?billing=success",
        checkout_cancel_url="https://staging.gridcheck.de/settings?billing=cancel",
        portal_return_url="https://staging.gridcheck.de/settings",
    )

    settings = config_module.load_settings()

    assert settings.app_env == "staging"
    assert settings.stripe_secret_key == "sk_test_staging_123"
    assert settings.stripe_price_pro_license_id == "price_pro_license_123"


def test_load_settings_accepts_cors_origin_regex_in_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("APP_VERSION", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://gridcheck:gridcheck_dev_2026@localhost:5433/gridcheck")
    monkeypatch.setenv("CORS_ORIGIN_REGEX", r"^https://[a-z0-9-]+\.up\.railway\.app$")
    monkeypatch.setenv("JWT_SECRET", "pytest-gridcheck-access-secret-32-chars")
    monkeypatch.setenv("JWT_REFRESH_SECRET", "pytest-gridcheck-refresh-secret-32")

    settings = config_module.load_settings()

    assert settings.cors_origin_regex == r"^https://[a-z0-9-]+\.up\.railway\.app$"
    assert settings.cors_origins == []


def test_load_settings_rejects_invalid_cors_origin_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    _set_base_env(monkeypatch, app_env="staging")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setenv("CORS_ORIGIN_REGEX", "[")

    with pytest.raises(RuntimeError, match="CORS_ORIGIN_REGEX muss ein gueltiger Regex sein"):
        config_module.load_settings()
