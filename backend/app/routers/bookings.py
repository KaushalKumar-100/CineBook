from datetime import datetime
from decimal import Decimal
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, get_current_user
from app.models import Booking, BookingItem, BookingTicket, Event, Movie, Payment, Seat, SessionEvent, TicketType, User, VenueSpace
from app.schemas import BookingCreate, BookingOut, PaymentOut

router = APIRouter(prefix="/bookings", tags=["Bookings"])


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
