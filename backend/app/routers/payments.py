import json
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import DbSession, get_current_user
from app.models import Booking, BookingTicket, Notification, Payment, RefundRequest, User
from app.razorpay import (
    amount_in_paise,
    configured,
    create_refund,
    fetch_payment,
    verify_checkout_signature,
    verify_webhook_signature,
)
from app.schemas import BookingOut, PaymentVerify

router = APIRouter(prefix="/payments", tags=["Payments"])


def _payment_for_order(db, order_id: str) -> Payment | None:
    return db.scalar(select(Payment).where(
        Payment.provider == "razorpay", Payment.provider_reference == order_id
    ).with_for_update())


def _confirm_captured_payment(db, payment: Payment, provider_payment: dict):
    if provider_payment.get("order_id") != payment.provider_reference:
        raise HTTPException(status_code=409, detail="Payment does not belong to this CineBook order")
    if provider_payment.get("status") != "captured":
        raise HTTPException(status_code=409, detail="Razorpay has not captured this payment")
    if int(provider_payment.get("amount", -1)) != amount_in_paise(payment.amount):
        raise HTTPException(status_code=409, detail="Captured amount does not match the server-calculated booking total")

    if payment.status in {"succeeded", "refunded"}:
        if payment.provider_payment_id != provider_payment.get("id"):
            raise HTTPException(status_code=409, detail="A different payment is already recorded for this order")
        return db.get(Booking, payment.booking_id)
    if payment.status != "initiated":
        raise HTTPException(status_code=409, detail="This payment order is no longer payable")

    booking = db.scalar(select(Booking).where(Booking.id == payment.booking_id).with_for_update())
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    payment.provider_payment_id = provider_payment["id"]
    payment.paid_at = datetime.now()
    if booking.status != "pending" or (booking.expires_at and booking.expires_at <= datetime.now()):
        # A capture after the inventory hold expired cannot create a valid ticket.
        # Request a full refund and leave inventory available for other customers.
        create_refund(provider_payment["id"], payment.amount, booking.booking_reference)
        payment.status = "refunded"
        booking.status = "expired"
        db.commit()
        return booking

    booking.status = "confirmed"
    booking.expires_at = None
    ticket_code = secrets.token_urlsafe(24).replace("-", "").replace("_", "").upper()[:32]
    booking.ticket_code = ticket_code
    payment.status = "succeeded"
    db.add(BookingTicket(booking_id=booking.id, ticket_code=ticket_code))
    db.add(Notification(
        user_id=booking.user_id,
        title="Booking confirmed",
        message=f"Payment verified for booking {booking.booking_reference}. Your ticket is ready.",
        kind="booking",
        link=f"/bookings/{booking.id}",
    ))
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/config")
def payment_config():
    settings = get_settings()
    return {"razorpay_enabled": configured(), "razorpay_key_id": settings.razorpay_key_id if configured() else None}


@router.post("/razorpay/verify")
def verify_razorpay_payment(
    payload: PaymentVerify,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
):
    if not configured():
        raise HTTPException(status_code=503, detail="Razorpay is not configured")
    if not verify_checkout_signature(payload.razorpay_order_id, payload.razorpay_payment_id, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay payment signature")
    payment = _payment_for_order(db, payload.razorpay_order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="CineBook payment order not found")
    booking = db.get(Booking, payment.booking_id)
    if not booking or (booking.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Booking not found")
    provider_payment = fetch_payment(payload.razorpay_payment_id)
    booking = _confirm_captured_payment(db, payment, provider_payment)
    return {"booking": BookingOut.model_validate(booking), "payment_status": payment.status}


@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, db: DbSession):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay webhook signature")
    try:
        event = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event_type = event.get("event")
    payload = event.get("payload", {})
    if event_type in {"payment.captured", "order.paid"}:
        entity = payload.get("payment", {}).get("entity")
        if not entity and event_type == "order.paid":
            entity = payload.get("payment", {}).get("entity")
        if not entity:
            return {"received": True, "processed": False}
        payment = _payment_for_order(db, str(entity.get("order_id", "")))
        if not payment:
            # Unknown orders belong to another integration; acknowledge safely.
            return {"received": True, "processed": False}
        _confirm_captured_payment(db, payment, entity)
    elif event_type == "payment.failed":
        # A failed attempt does not necessarily close a Razorpay order; the
        # customer may retry another payment method. The order hold expires by TTL.
        pass
    elif event_type == "refund.processed":
        # Refund status is recorded from the verified provider event; the refund
        # request itself is initiated by the admin workflow.
        refund_entity = payload.get("refund", {}).get("entity", {})
        payment_id = refund_entity.get("payment_id")
        payment = db.scalar(select(Payment).where(Payment.provider_payment_id == payment_id).with_for_update()) if payment_id else None
        if payment:
            payment.status = "refunded"
            refund_request = db.scalar(select(RefundRequest).where(RefundRequest.payment_id == payment.id).with_for_update())
            if refund_request and refund_request.status in {"approved", "processing"}:
                refund_request.status = "processed"
                db.add(Notification(user_id=refund_request.user_id, title="Refund completed", message=f"Your refund for booking {refund_request.booking_id} has been completed.", kind="refund"))
            db.commit()
    elif event_type == "refund.failed":
        refund_entity = payload.get("refund", {}).get("entity", {})
        payment_id = refund_entity.get("payment_id")
        payment = db.scalar(select(Payment).where(Payment.provider_payment_id == payment_id).with_for_update()) if payment_id else None
        if payment:
            refund_request = db.scalar(select(RefundRequest).where(RefundRequest.payment_id == payment.id).with_for_update())
            if refund_request and refund_request.status in {"approved", "processing"}:
                refund_request.status = "failed"
                refund_request.booking.status = "confirmed"
                db.add(Notification(user_id=refund_request.user_id, title="Refund failed", message=f"Your refund for booking {refund_request.booking_id} failed. Contact support for help.", kind="refund"))
            db.commit()
    return {"received": True, "processed": True}
