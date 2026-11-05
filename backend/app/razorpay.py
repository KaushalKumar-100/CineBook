"""Small server-side Razorpay adapter. Secrets never leave the backend."""
import hashlib
import hmac
from decimal import Decimal

import httpx
from fastapi import HTTPException

from app.config import get_settings

BASE_URL = "https://api.razorpay.com/v1"


def configured() -> bool:
    settings = get_settings()
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


def amount_in_paise(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1")))


def _client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret), timeout=15)


def create_order(amount: Decimal, receipt: str) -> dict:
    try:
        with _client() as client:
            response = client.post(f"{BASE_URL}/orders", json={
                "amount": amount_in_paise(amount), "currency": "INR", "receipt": receipt,
                "notes": {"cinebook_reference": receipt},
            })
            response.raise_for_status()
            order = response.json()
            if not isinstance(order, dict) or not order.get("id"):
                raise ValueError("Razorpay response did not include an order ID")
            return order
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Razorpay order could not be created. No payment was taken.") from exc


def fetch_payment(payment_id: str) -> dict:
    try:
        with _client() as client:
            response = client.get(f"{BASE_URL}/payments/{payment_id}")
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Razorpay payment status could not be verified.") from exc


def create_refund(payment_id: str, amount: Decimal, receipt: str) -> dict:
    try:
        with _client() as client:
            response = client.post(f"{BASE_URL}/payments/{payment_id}/refund", json={
                "amount": amount_in_paise(amount), "receipt": receipt,
                "notes": {"cinebook_reference": receipt},
            })
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Razorpay refund request could not be created.") from exc


def verify_checkout_signature(order_id: str, payment_id: str, signature: str) -> bool:
    secret = get_settings().razorpay_key_secret.encode()
    expected = hmac.new(secret, f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = get_settings().razorpay_webhook_secret
    if not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
