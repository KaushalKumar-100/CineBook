from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.dependencies import DbSession
from app.models import Booking, BookingItem, City, Event, EventCategory, Movie, Seat, SessionEvent, ShowSeatHold, TicketType, Venue, VenueSpace

router = APIRouter(tags=["Discovery"])


def _seat_price(db, session_id: int, seat: Seat, base_price: Decimal):
    configured = db.scalar(select(TicketType.price).where(
        TicketType.session_id == session_id,
        TicketType.name.ilike(seat.seat_category),
        TicketType.is_active.is_(True),
    ).limit(1))
    return configured if configured is not None else base_price


@router.get("/cities")
def list_cities(db: DbSession):
    return db.scalars(select(City).order_by(City.name)).all()


@router.get("/venues")
def list_venues(
    db: DbSession,
    city_id: int | None = None,
    q: str | None = Query(default=None, max_length=120),
    venue_type: str | None = Query(default=None, max_length=40),
):
    stmt = (
        select(Venue)
        .where(Venue.is_active.is_(True))
        .options(joinedload(Venue.city))
        .order_by(Venue.name)
    )
    if city_id is not None:
        stmt = stmt.where(Venue.city_id == city_id)
    if q:
        stmt = stmt.where(Venue.name.ilike(f"%{q}%"))
    if venue_type:
        stmt = stmt.where(Venue.venue_type == venue_type)
    venues = db.scalars(stmt).unique().all()
    result = []
    for venue in venues:
        spaces = db.scalars(select(VenueSpace).where(VenueSpace.venue_id == venue.id)).all()
        result.append({
            "id": venue.id, "city_id": venue.city_id,
            "city": {"id": venue.city.id, "name": venue.city.name, "state": venue.city.state},
            "name": venue.name, "venue_type": venue.venue_type, "address": venue.address,
            "contact_number": venue.contact_number, "images": [],
            "capacity": sum(space.capacity for space in spaces),
            "spaces": [{"id": space.id, "name": space.name, "space_type": space.space_type, "capacity": space.capacity} for space in spaces],
        })
    return result


@router.get("/venues/{venue_id}")
def get_venue(venue_id: int, db: DbSession):
    venue = db.scalar(select(Venue).where(Venue.id == venue_id, Venue.is_active.is_(True)).options(joinedload(Venue.city)))
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    spaces = db.scalars(select(VenueSpace).where(VenueSpace.venue_id == venue.id).order_by(VenueSpace.name)).all()
    return {
        "id": venue.id, "name": venue.name, "venue_type": venue.venue_type,
        "address": venue.address, "contact_number": venue.contact_number,
        "city": {"id": venue.city.id, "name": venue.city.name, "state": venue.city.state, "country": venue.city.country},
        "capacity": sum(space.capacity for space in spaces),
        "spaces": [{"id": space.id, "name": space.name, "space_type": space.space_type, "capacity": space.capacity} for space in spaces],
    }


@router.get("/venues/{venue_id}/events")
def list_venue_events(
    venue_id: int,
    db: DbSession,
    category_id: int | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    sort: str = Query(default="date", pattern="^(date|price)$"),
):
    venue = db.get(Venue, venue_id)
    if not venue or not venue.is_active:
        raise HTTPException(status_code=404, detail="Venue not found")
    stmt = select(Event).where(
        Event.venue_id == venue_id,
        Event.status == "published",
    ).options(joinedload(Event.city), joinedload(Event.category))
    if category_id is not None:
        stmt = stmt.where(Event.category_id == category_id)
    events = db.scalars(stmt).unique().all()
    result = []
    for event in events:
        sessions = db.scalars(
            select(SessionEvent)
            .join(VenueSpace, SessionEvent.venue_space_id == VenueSpace.id)
            .where(
                SessionEvent.event_id == event.id,
                SessionEvent.status == "scheduled",
                SessionEvent.starts_at >= datetime.now(),
                VenueSpace.venue_id == venue_id,
            ).order_by(SessionEvent.starts_at)
        ).all()
        sessions = [
            session for session in sessions
            if (from_date is None or session.starts_at >= from_date)
            and (to_date is None or session.starts_at <= to_date)
        ]
        if not sessions:
            continue
        prices = []
        for session in sessions:
            prices.extend(db.scalars(select(TicketType.price).where(
                TicketType.session_id == session.id, TicketType.is_active.is_(True)
            )).all())
        starting_price = min(prices) if prices else min(session.base_price for session in sessions)
        if min_price is not None and starting_price < min_price:
            continue
        if max_price is not None and starting_price > max_price:
            continue
        result.append({
            "id": event.id, "title": event.title, "description": event.description,
            "event_type": event.event_type, "poster_url": event.poster_url,
            "category": {"id": event.category.id, "name": event.category.name},
            "city": {"id": event.city.id, "name": event.city.name},
            "venue": {"id": venue.id, "name": venue.name, "address": venue.address, "venue_type": venue.venue_type},
            "starts_at": sessions[0].starts_at, "starting_price": starting_price,
            "availability": "upcoming",
            "sessions": [{
                "id": session.id, "starts_at": session.starts_at, "ends_at": session.ends_at,
                "base_price": session.base_price, "tax_percent": session.tax_percent,
                "convenience_fee": session.convenience_fee,
            } for session in sessions],
        })
    result.sort(key=lambda item: item["starting_price"] if sort == "price" else item["starts_at"])
    return result


@router.get("/venues/{venue_id}/spaces")
def venue_spaces(venue_id: int, db: DbSession):
    if not db.get(Venue, venue_id):
        raise HTTPException(status_code=404, detail="Venue not found")
    return db.scalars(
        select(VenueSpace).where(VenueSpace.venue_id == venue_id).order_by(VenueSpace.name)
    ).all()


@router.get("/venue-spaces/{space_id}/seats")
def venue_space_seat_layout(space_id: int, db: DbSession):
    space = db.get(VenueSpace, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Venue space not found")
    seats = db.scalars(
        select(Seat).where(Seat.venue_space_id == space_id).order_by(Seat.row_label, Seat.seat_number)
    ).all()
    return {
        "venue_space_id": space.id,
        "name": space.name,
        "capacity": space.capacity,
        "seat_count": len(seats),
        "seats": [{
            "id": seat.id, "row_label": seat.row_label,
            "seat_number": seat.seat_number, "seat_category": seat.seat_category,
        } for seat in seats],
    }


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
            "starts_at": upcoming.starts_at if upcoming else None,
            "starting_price": upcoming.base_price if upcoming else None,
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
    active_holds = db.scalars(select(ShowSeatHold).where(
        ShowSeatHold.session_id == session_id,
        ShowSeatHold.expires_at > datetime.now(),
    )).all()
    holds_by_seat = {hold.seat_id: hold for hold in active_holds}
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
        "tax_percent": session.tax_percent,
        "convenience_fee": session.convenience_fee,
        "status": session.status,
        "booking_mode": "seats" if session.booking_mode == "assigned" else "general_admission",
        "seats": [
            {
                "id": seat.id,
                "row_label": seat.row_label,
                "seat_number": seat.seat_number,
                "seat_type": seat.seat_type,
                "seat_category": seat.seat_category,
                "price": _seat_price(db, session_id, seat, session.base_price),
                "status": "booked" if seat.id in booked_seat_ids else ("locked" if seat.id in holds_by_seat else "available"),
                "available": seat.id not in booked_seat_ids and seat.id not in holds_by_seat,
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
    sessions = db.scalars(stmt).all()
    result = []
    for session in sessions:
        space = session.venue_space
        venue = space.venue if space else None
        result.append({
            "id": session.id,
            "event_id": session.event_id,
            "movie_id": session.movie_id,
            "venue_space_id": session.venue_space_id,
            "venue_space": {"id": space.id, "name": space.name} if space else None,
            "venue": {
                "id": venue.id, "name": venue.name, "address": venue.address,
            } if venue else None,
            "starts_at": session.starts_at,
            "ends_at": session.ends_at,
            "base_price": session.base_price,
            "tax_percent": session.tax_percent,
            "convenience_fee": session.convenience_fee,
            "status": session.status,
        })
    return result
