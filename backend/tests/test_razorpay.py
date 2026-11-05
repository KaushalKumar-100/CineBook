from decimal import Decimal
from types import SimpleNamespace
import hashlib
import hmac

import app.razorpay as razorpay


def test_amount_uses_integer_paise():
    assert razorpay.amount_in_paise(Decimal("499.50")) == 49950


def test_checkout_signature_is_compared_with_server_secret(monkeypatch):
    monkeypatch.setattr(razorpay, "get_settings", lambda: SimpleNamespace(razorpay_key_secret="test-secret"))
    message = b"order_test_123|pay_test_456"
    signature = hmac.new(b"test-secret", message, hashlib.sha256).hexdigest()

    assert razorpay.verify_checkout_signature("order_test_123", "pay_test_456", signature)
    assert not razorpay.verify_checkout_signature("order_test_123", "pay_other", signature)


def test_webhook_signature_requires_configured_secret(monkeypatch):
    body = b'{"event":"payment.captured"}'
    monkeypatch.setattr(razorpay, "get_settings", lambda: SimpleNamespace(razorpay_webhook_secret="hook-secret"))
    signature = hmac.new(b"hook-secret", body, hashlib.sha256).hexdigest()

    assert razorpay.verify_webhook_signature(body, signature)
    assert not razorpay.verify_webhook_signature(body + b" ", signature)


def test_webhook_signature_fails_closed_without_secret(monkeypatch):
    monkeypatch.setattr(razorpay, "get_settings", lambda: SimpleNamespace(razorpay_webhook_secret=""))

    assert not razorpay.verify_webhook_signature(b"{}", "anything")
