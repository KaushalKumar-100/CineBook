from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.dependencies import DbSession
from app.models import Booking, BookingItem, City, Event, EventCategory, Movie, Seat, SessionEvent, TicketType, Venue, VenueSpace

router = APIRouter(tags=["Discovery"])


@router.get("/cities")
def list_cities(db: DbSession):
    return db.scalars(select(City).order_by(City.name)).all()


@router.get("/venues")
def list_venues(db: DbSession, city_id: int | None = None):
    stmt = (
        select(Venue)
        .where(Venue.is_active.is_(True))
        .options(joinedload(Venue.city))
        .order_by(Venue.name)
    )
    if city_id is not None:
        stmt = stmt.where(Venue.city_id == city_id)
    return db.scalars(stmt).unique().all()


@router.get("/venues/{venue_id}/spaces")
def venue_spaces(venue_id: int, db: DbSession):
    if not db.get(Venue, venue_id):
        raise HTTPException(status_code=404, detail="Venue not found")
    return db.scalars(
        select(VenueSpace).where(VenueSpace.venue_id == venue_id).order_by(VenueSpace.name)
    ).all()


@router.get("/movies")
def list_movies(db: DbSession, q: str | None = Query(default=None, max_length=120)):
    stmt = select(Movie).where(Movie.is_active.is_(True)).order_by(Movie.title)
    if q:
        stmt = stmt.where(Movie.title.ilike(f"%{q}%"))
    return db.scalars(stmt).all()


@router.get("/events")
def list_events(
    db: DbSession,
    city_id: int | None = None,
    category_id: int | None = None,
    event_type: str | None = Query(default=None, pattern="^(local|major)$"),
    q: str | None = Query(default=None, max_length=120),
):
    stmt = (
        select(Event)
        .where(Event.status == "published")
        .options(joinedload(Event.city), joinedload(Event.venue), joinedload(Event.category))
        .order_by(Event.created_at.desc())
    )
    if city_id is not None:
        stmt = stmt.where(Event.city_id == city_id)
    if category_id is not None:
        stmt = stmt.where(Event.category_id == category_id)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if q:
        stmt = stmt.where(Event.title.ilike(f"%{q}%"))
    events = db.scalars(stmt).unique().all()
    if not events:
        return []

    # Fetch upcoming sessions in one additional query instead of running one
    # query per event. This avoids the classic N+1 query pattern as catalog size grows.
    now = datetime.now()
    event_ids = [event.id for event in events]
    upcoming_sessions = db.scalars(
        select(SessionEvent)
        .where(
            SessionEvent.event_id.in_(event_ids),
            SessionEvent.status == "scheduled",
            SessionEvent.starts_at >= now,
        )
        .order_by(SessionEvent.starts_at)
    ).all()
    upcoming_by_event = {}
    for session in upcoming_sessions:
        upcoming_by_event.setdefault(session.event_id, session)

    result = []
    for event in events:
        upcoming = upcoming_by_event.get(event.id)
        result.append({
            "id": event.id,
            "organizer_id": event.organizer_id,
            "city_id": event.city_id,
            "category_id": event.category_id,
            "venue_id": event.venue_id,
            "title": event.title,
            "description": event.description,
            "event_type": event.event_type,
            "status": event.status,
            "poster_url": event.poster_url,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
            "city": {
                "id": event.city.id,
                "name": event.city.name,
                "state": event.city.state,
                "country": event.city.country,
            },
            "venue": {
                "id": event.venue.id,
                "name": event.venue.name,
                "venue_type": event.venue.venue_type,
                "address": event.venue.address,
            },
            "category": {
                "id": event.category.id,
                "name": event.category.name,
                "description": event.category.description,
            },
            "session_id": upcoming.id if upcoming else None,
            "starts_at": upcoming.starts_at if upcoming else None,
            "ends_at": upcoming.ends_at if upcoming else None,
        })
    return result


@router.get("/event-categories")
def list_categories(db: DbSession):
    return db.scalars(select(EventCategory).order_by(EventCategory.name)).all()



@router.get("/sessions/{session_id}/availability")
def session_availability(session_id: int, db: DbSession):
    session = db.get(SessionEvent, session_id)
    if not session or session.status != "scheduled":
        raise HTTPException(status_code=404, detail="Scheduled session not found")
    if session.event_id is not None and (not session.event or session.event.status != "published"):
        raise HTTPException(status_code=404, detail="Published event session not found")
    if session.movie_id is not None and (not session.movie or not session.movie.is_active):
        raise HTTPException(status_code=404, detail="Active movie session not found")
    booked_seat_ids = set(db.scalars(
        select(BookingItem.seat_id)
        .join(Booking, BookingItem.booking_id == Booking.id)
        .where(
            Booking.session_id == session_id,
            Booking.status == "confirmed",
            BookingItem.seat_id.is_not(None),
        )
    ).all())
    seats = db.scalars(
        select(Seat)
        .where(Seat.venue_space_id == session.venue_space_id)
        .order_by(Seat.row_label, Seat.seat_number)
    ).all()
    ticket_types = db.scalars(
        select(TicketType)
        .where(TicketType.session_id == session_id, TicketType.is_active.is_(True))
        .order_by(TicketType.price, TicketType.name)
    ).all()
    # Aggregate sold quantities for every ticket type in one database roundtrip.
    sold_by_ticket = {}
    if ticket_types:
        sold_rows = db.execute(
            select(BookingItem.ticket_type_id, func.coalesce(func.sum(BookingItem.quantity), 0))
            .join(Booking, BookingItem.booking_id == Booking.id)
            .where(
                Booking.session_id == session_id,
                Booking.status == "confirmed",
                BookingItem.ticket_type_id.in_([ticket.id for ticket in ticket_types]),
            )
            .group_by(BookingItem.ticket_type_id)
        ).all()
        sold_by_ticket = {ticket_id: int(quantity or 0) for ticket_id, quantity in sold_rows}
    ticket_availability = []
    for ticket in ticket_types:
        sold = sold_by_ticket.get(ticket.id, 0)
        ticket_availability.append({
            "id": ticket.id,
            "name": ticket.name,
            "description": ticket.description,
            "price": ticket.price,
            "capacity": ticket.capacity,
            "remaining": max(0, ticket.capacity - sold),
        })
    return {
        "session_id": session.id,
        "event_id": session.event_id,
        "movie_id": session.movie_id,
        "venue_space_id": session.venue_space_id,
        "starts_at": session.starts_at,
        "ends_at": session.ends_at,
        "base_price": session.base_price,
        "status": session.status,
        "booking_mode": "seats" if session.movie_id is not None else "general_admission",
        "seats": [
            {
                "id": seat.id,
                "row_label": seat.row_label,
                "seat_number": seat.seat_number,
                "seat_type": seat.seat_type,
                "available": seat.id not in booked_seat_ids,
            }
            for seat in seats
        ],
        "ticket_types": ticket_availability,
    }

@router.get("/sessions")
def list_sessions(
    db: DbSession,
    event_id: int | None = None,
    movie_id: int | None = None,
    from_time: datetime | None = None,
):
    stmt = (
        select(SessionEvent)
        .outerjoin(Event, SessionEvent.event_id == Event.id)
        .outerjoin(Movie, SessionEvent.movie_id == Movie.id)
        .where(
            SessionEvent.status == "scheduled",
            or_(SessionEvent.event_id.is_(None), Event.status == "published"),
            or_(SessionEvent.movie_id.is_(None), Movie.is_active.is_(True)),
        )
        .order_by(SessionEvent.starts_at)
    )
    if event_id is not None:
        stmt = stmt.where(SessionEvent.event_id == event_id)
    if movie_id is not None:
        stmt = stmt.where(SessionEvent.movie_id == movie_id)
    if from_time:
        stmt = stmt.where(SessionEvent.starts_at >= from_time)
    return db.scalars(stmt).all()
