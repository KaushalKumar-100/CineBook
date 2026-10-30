import pytest

from app.config import Settings


def test_production_requires_demo_mode_disabled():
    with pytest.raises(ValueError, match="DEMO_MODE must be false"):
        Settings(app_env="production", demo_mode=True, secret_key="a" * 48)


def test_production_rejects_development_secret():
    with pytest.raises(ValueError, match="unique SECRET_KEY"):
        Settings(
            app_env="production",
            demo_mode=False,
            secret_key="development-only-change-this-secret",
            razorpay_key_id="rzp_test_dummy",
            razorpay_key_secret="test_secret_dummy",
            razorpay_webhook_secret="test_webhook_secret_dummy",
        )


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValueError, match="Wildcard CORS"):
        Settings(
            app_env="production",
            demo_mode=False,
            secret_key="r" * 48,
            cors_allowed_origins="*",
            razorpay_key_id="rzp_test_dummy",
            razorpay_key_secret="test_secret_dummy",
            razorpay_webhook_secret="test_webhook_secret_dummy",
        )


def test_production_accepts_explicit_frontend_origin():
    settings = Settings(
        app_env="production",
        demo_mode=False,
        secret_key="r" * 48,
        cors_allowed_origins="https://cinebook.example",
        razorpay_key_id="rzp_test_dummy",
        razorpay_key_secret="test_secret_dummy",
        razorpay_webhook_secret="test_webhook_secret_dummy",
    )
    assert settings.app_env == "production"
    assert settings.cors_allowed_origins == "https://cinebook.example"
