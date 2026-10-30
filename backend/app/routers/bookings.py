import base64
from datetime import datetime, timedelta
from io import BytesIO
from decimal import Decimal
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
import qrcode
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.dependencies import DbSession, get_current_user
from app.models import Booking, BookingItem, BookingTicket, Event, Movie, Payment, Seat, SessionEvent, ShowSeatHold, TicketType, User, VenueSpace
from app.schemas import BookingCreate, BookingOut, PaymentOut, SeatHoldCreate

router = APIRouter(prefix="/bookings", tags=["Bookings"])
settings = get_settings()





def build_ticket_qr_data_url(ticket_code: str) -> str:
    """Create a PNG QR data URL containing only the unguessable ticket code."""
    image = qrcode.make(ticket_code, box_size=8, border=4)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@router.post("/holds")
def hold_seats(
    payload: SeatHoldCreate,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
):
    """Temporarily reserve cinema seats for the signed-in user.

    Locking the parent session row serializes hold acquisition and booking
    attempts for the same show on MySQL/InnoDB.
    """
    seat_ids = payload.seat_ids
    if len(set(seat_ids)) != len(seat_ids):
        raise HTTPException(status_code=422, detail="Duplicate seat IDs are not allowed")

    now = datetime.now()
    try:
        session = db.scalar(
            select(SessionEvent)
            .where(SessionEvent.id == payload.session_id, SessionEvent.status == "scheduled")
            .with_for_update()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Scheduled session not found")
        if session.booking_mode != "assigned":
            raise HTTPException(status_code=422, detail="This session uses general-admission tickets, not assigned seats")
        if session.starts_at <= now:
            raise HTTPException(status_code=409, detail="This session has already started")

        seats = db.scalars(
            select(Seat)
            .where(Seat.id.in_(seat_ids), Seat.venue_space_id == session.venue_space_id)
            .with_for_update()
        ).all()
        if len(seats) != len(seat_ids):
            raise HTTPException(status_code=422, detail="A seat does not belong to this session screen")

        booked = set(db.scalars(
            select(BookingItem.seat_id)
            .join(Booking, BookingItem.booking_id == Booking.id)
            .where(
                Booking.session_id == session.id,
                Booking.status == "confirmed",
                BookingItem.seat_id.in_(seat_ids),
            )
            .with_for_update()
        ).all())
        if booked:
            raise HTTPException(status_code=409, detail="One or more selected seats are already booked")

        # Expired rows no longer block inventory. Remove them opportunistically
        # whenever someone tries to acquire seats for this session.
        db.execute(delete(ShowSeatHold).where(
            ShowSeatHold.session_id == session.id,
            ShowSeatHold.expires_at <= now,
        ))

        active_holds = db.scalars(
            select(ShowSeatHold)
            .where(
                ShowSeatHold.session_id == session.id,
                ShowSeatHold.seat_id.in_(seat_ids),
                ShowSeatHold.expires_at > now,
            )
            .with_for_update()
        ).all()
        holds_by_seat = {hold.seat_id: hold for hold in active_holds}
        conflicts = [
            seat_id for seat_id, hold in holds_by_seat.items()
            if hold.user_id != user.id
        ]
        if conflicts:
            raise HTTPException(
                status_code=409,
                detail="One or more selected seats are temporarily held by another customer",
            )

        # Selecting a new set replaces this user's previous unexpired selection
        # for the same show, releasing seats they no longer want.
        db.execute(delete(ShowSeatHold).where(
            ShowSeatHold.session_id == session.id,
            ShowSeatHold.user_id == user.id,
            ShowSeatHold.expires_at > now,
            ShowSeatHold.seat_id.not_in(seat_ids),
        ))

        expires_at = now + timedelta(minutes=settings.seat_hold_minutes)
        for seat_id in seat_ids:
            hold = holds_by_seat.get(seat_id)
            if hold is None:
                db.add(ShowSeatHold(
                    session_id=session.id,
                    seat_id=seat_id,
                    user_id=user.id,
                    expires_at=expires_at,
                ))
            else:
                hold.expires_at = expires_at

        db.commit()
        return {
            "session_id": session.id,
            "seat_ids": seat_ids,
            "expires_at": expires_at,
            "hold_minutes": settings.seat_hold_minutes,
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Seat inventory changed; refresh availability and retry")


@router.delete("/holds/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def release_seat_holds(
    session_id: int,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
):
    session = db.scalar(
        select(SessionEvent).where(SessionEvent.id == session_id).with_for_update()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.execute(delete(ShowSeatHold).where(
        ShowSeatHold.session_id == session_id,
        ShowSeatHold.user_id == user.id,
    ))
    db.commit()
    return None


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    # Validate allocation choice before creating any records.
    has_seats = payload.seat_ids is not None
    has_ticket = payload.ticket_type_id is not None
    if has_seats == has_ticket:
        raise HTTPException(status_code=422, detail="Choose either seat_ids or ticket_type_id")
    if has_seats and not payload.seat_ids:
        raise HTTPException(status_code=422, detail="seat_ids cannot be empty")
    if has_seats and payload.quantity != 1:
        raise HTTPException(status_code=422, detail="Use quantity=1 when booking assigned seats")

    try:
        # Serialize booking attempts for the same scheduled session on MySQL/InnoDB.
        session = db.scalar(select(SessionEvent).where(
            SessionEvent.id == payload.session_id, SessionEvent.status == "scheduled"
        ).with_for_update())
        if not session:
            raise HTTPException(status_code=404, detail="Scheduled session not found")
        if session.event_id is not None:
            event = db.get(Event, session.event_id)
            if not event or event.status != "published":
                raise HTTPException(status_code=404, detail="Published event session not found")
        if session.movie_id is not None:
            movie = db.get(Movie, session.movie_id)
            if not movie or not movie.is_active:
                raise HTTPException(status_code=404, detail="Active movie session not found")
        if session.starts_at <= datetime.now():
            raise HTTPException(status_code=409, detail="This session has already started")
        if has_seats and session.booking_mode != "assigned":
            raise HTTPException(status_code=422, detail="This session uses general-admission tickets")
        if has_ticket and session.booking_mode != "general_admission":
            raise HTTPException(status_code=422, detail="This session uses assigned seats")

        booking = Booking(
            booking_reference=token_urlsafe(12).replace("-", "").replace("_", "").upper()[:22],
            user_id=user.id, session_id=session.id, status="confirmed",
            total_amount=Decimal("0.00"), subtotal_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"), convenience_amount=Decimal("0.00"),
        )
        db.add(booking)
        db.flush()
        total = Decimal("0.00")

        if has_seats:
            seat_ids = payload.seat_ids or []
            if len(set(seat_ids)) != len(seat_ids):
                raise HTTPException(status_code=422, detail="Duplicate seat IDs are not allowed")
            seats = db.scalars(select(Seat).join(VenueSpace, Seat.venue_space_id == VenueSpace.id)
                .where(Seat.id.in_(seat_ids), VenueSpace.id == session.venue_space_id)
                .with_for_update()).all()
            if len(seats) != len(seat_ids):
                raise HTTPException(status_code=422, detail="A seat does not belong to this session space")
            taken = db.scalars(select(BookingItem.seat_id).join(Booking, BookingItem.booking_id == Booking.id)
                .where(Booking.session_id == session.id, Booking.status == "confirmed",
                       BookingItem.seat_id.in_(seat_ids)).with_for_update()).all()
            if taken:
                raise HTTPException(status_code=409, detail="One or more seats are already booked")

            live_holds = db.scalars(select(ShowSeatHold).where(
                ShowSeatHold.session_id == session.id,
                ShowSeatHold.seat_id.in_(seat_ids),
                ShowSeatHold.expires_at > datetime.now(),
            ).with_for_update()).all()
            held_by_seat = {hold.seat_id: hold for hold in live_holds}
            if any(
                seat_id not in held_by_seat or held_by_seat[seat_id].user_id != user.id
                for seat_id in seat_ids
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Your seat hold has expired or belongs to another customer. Select the seats again.",
                )

            for seat in seats:
                configured_price = db.scalar(select(TicketType.price).where(
                    TicketType.session_id == session.id,
                    TicketType.name.ilike(seat.seat_category),
                    TicketType.is_active.is_(True),
                ).limit(1))
                unit_price = configured_price if configured_price is not None else session.base_price
                db.add(BookingItem(booking_id=booking.id, seat_id=seat.id, quantity=1, unit_price=unit_price))
                total += unit_price
        else:
            ticket = db.scalar(select(TicketType).where(
                TicketType.id == payload.ticket_type_id, TicketType.session_id == session.id,
                TicketType.is_active.is_(True)).with_for_update())
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket type not found for this session")
            # Lock the parent session row above; this serializes quantity checks for
            # this session across concurrent MySQL/InnoDB booking transactions.
            sold = db.scalar(select(func.coalesce(func.sum(BookingItem.quantity), 0))
                .join(Booking, BookingItem.booking_id == Booking.id)
                .where(Booking.session_id == session.id, Booking.status == "confirmed",
                       BookingItem.ticket_type_id == ticket.id)) or 0
            if sold + payload.quantity > ticket.capacity:
                raise HTTPException(status_code=409, detail="Not enough tickets remaining")
            total = ticket.price * payload.quantity
            db.add(BookingItem(booking_id=booking.id, ticket_type_id=ticket.id,
                               quantity=payload.quantity, unit_price=ticket.price))

        tax_amount = (total * (session.tax_percent or Decimal("0.00")) / Decimal("100.00")).quantize(Decimal("0.01"))
        convenience_amount = session.convenience_fee or Decimal("0.00")
        grand_total = total + tax_amount + convenience_amount
        booking.subtotal_amount = total
        booking.tax_amount = tax_amount
        booking.convenience_amount = convenience_amount
        booking.total_amount = grand_total
        ticket_code = token_urlsafe(18).replace("-", "").replace("_", "").upper()[:32]
        booking.ticket_code = ticket_code
        db.add(BookingTicket(booking_id=booking.id, ticket_code=ticket_code))
        # Demo-only payment confirmation. No card/UPI credentials are collected.
        db.add(Payment(booking_id=booking.id, provider=payload.payment_method, amount=grand_total, status="succeeded"))
        if has_seats:
            db.execute(delete(ShowSeatHold).where(
                ShowSeatHold.session_id == session.id,
                ShowSeatHold.seat_id.in_(payload.seat_ids or []),
                ShowSeatHold.user_id == user.id,
            ))
        db.commit()
        db.refresh(booking)
        return booking
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Booking conflicted with another request; please retry")


@router.get("/me", response_model=list[BookingOut])
def my_bookings(db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    return db.scalars(select(Booking).where(Booking.user_id == user.id).order_by(Booking.created_at.desc())).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    booking = db.get(Booking, booking_id)
    if not booking or (booking.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking



@router.get("/{booking_id}/ticket/qr")
def get_booking_ticket_qr(
    booking_id: int,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
):
    """Return a downloadable QR image after a confirmed booking."""
    booking = db.get(Booking, booking_id)
    if not booking or (booking.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "confirmed" or not booking.ticket_code:
        raise HTTPException(status_code=409, detail="A confirmed ticket is not available for this booking")

    ticket = db.scalar(select(BookingTicket).where(
        BookingTicket.booking_id == booking.id,
        BookingTicket.ticket_code == booking.ticket_code,
    ))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket record not found")

    return {
        "booking_reference": booking.booking_reference,
        "ticket_code": ticket.ticket_code,
        "qr_code_data_url": build_ticket_qr_data_url(ticket.ticket_code),
        "format": "PNG",
        "contains": "ticket_code_only",
    }


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if not booking or (booking.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "confirmed":
        raise HTTPException(status_code=409, detail="Only confirmed bookings can be cancelled")
    booking.status = "cancelled"
    db.add(Payment(booking_id=booking.id, provider="demo", amount=booking.total_amount, status="refunded"))
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/{booking_id}/payments", response_model=list[PaymentOut])
def booking_payments(booking_id: int, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    booking = db.get(Booking, booking_id)
    if not booking or (booking.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Booking not found")
    return db.scalars(select(Payment).where(Payment.booking_id == booking_id).order_by(Payment.id)).all()
