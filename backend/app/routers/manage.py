from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, require_roles
from app.models import City, Event, EventCategory, Movie, Seat, SessionEvent, TicketType, User, Venue, VenueSpace
from app.schemas import CategoryCreate, CityCreate, EventCreate, MovieCreate, SessionCreate, TicketTypeCreate, VenueCreate, VenueSpaceCreate

router = APIRouter(prefix="/manage", tags=["Organizer and Admin"])


def save(db, item):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Record conflicts with existing data or violates a constraint")
    db.refresh(item)
    return item


@router.post("/cities", status_code=status.HTTP_201_CREATED)
def create_city(payload: CityCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    item = City(name=payload.name.strip(), state=payload.state.strip(), country=payload.country.strip())
    db.add(item)
    return save(db, item)


@router.post("/venues", status_code=status.HTTP_201_CREATED)
def create_venue(payload: VenueCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    item = Venue(**payload.model_dump())
    db.add(item)
    return save(db, item)


@router.post("/venue-spaces", status_code=status.HTTP_201_CREATED)
def create_space(payload: VenueSpaceCreate, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    venue = db.get(Venue, payload.venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    if user.role == "organizer":
        owns_venue = db.scalar(select(Event.id).where(Event.organizer_id == user.id, Event.venue_id == venue.id).limit(1))
        if not owns_venue:
            raise HTTPException(status_code=403, detail="You do not manage this venue")
    item = VenueSpace(**payload.model_dump())
    db.add(item)
    return save(db, item)


@router.post("/movies", status_code=status.HTTP_201_CREATED)
def create_movie(payload: MovieCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    movie_data = payload.model_dump()
    movie_data["poster_url"] = str(payload.poster_url) if payload.poster_url else None
    item = Movie(**movie_data)
    db.add(item)
    return save(db, item)


@router.post("/event-categories", status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    item = EventCategory(**payload.model_dump())
    db.add(item)
    return save(db, item)


@router.post("/ticket-types", status_code=status.HTTP_201_CREATED)
def create_ticket_type(payload: TicketTypeCreate, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    session = db.get(SessionEvent, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if user.role == "organizer" and session.event and session.event.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your event")
    if session.movie_id is not None:
        raise HTTPException(status_code=422, detail="Cinema sessions use numbered seats; ticket types are for general-admission events")
    sold_capacity = db.scalar(select(func.coalesce(func.sum(TicketType.capacity), 0)).where(TicketType.session_id == session.id)) or 0
    if sold_capacity + payload.capacity > session.venue_space.capacity:
        raise HTTPException(status_code=422, detail="Combined ticket-type capacity cannot exceed venue capacity")
    item = TicketType(**payload.model_dump())
    db.add(item)
    return save(db, item)


@router.post("/seats/bulk", status_code=status.HTTP_201_CREATED)
def create_seats(venue_space_id: int, rows: list[str], seats_per_row: int, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    if not db.get(VenueSpace, venue_space_id):
        raise HTTPException(status_code=404, detail="Venue space not found")
    if not rows or len(rows) > 100 or seats_per_row < 1 or seats_per_row > 1000:
        raise HTTPException(status_code=422, detail="Provide 1-100 rows and 1-1000 seats per row")
    if len(set(rows)) != len(rows) or any(not row or len(row) > 10 for row in rows):
        raise HTTPException(status_code=422, detail="Row labels must be unique and 1-10 characters")
    space = db.get(VenueSpace, venue_space_id)
    if user.role == "organizer":
        venue = db.get(Venue, space.venue_id)
        # Organizers can create seats only in a venue they manage by owning an event at that venue.
        owns_venue = db.scalar(select(Event.id).where(Event.organizer_id == user.id, Event.venue_id == venue.id).limit(1))
        if not owns_venue:
            raise HTTPException(status_code=403, detail="You do not manage this venue")
    existing = db.query(Seat).filter(Seat.venue_space_id == venue_space_id).count()
    requested_count = len(rows) * seats_per_row
    if existing + requested_count > space.capacity:
        raise HTTPException(status_code=422, detail="Seat count cannot exceed venue space capacity")
    items = [Seat(venue_space_id=venue_space_id, row_label=row, seat_number=n) for row in rows for n in range(1, seats_per_row + 1)]
    db.add_all(items)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Some seat positions already exist")
    return {"created": len(items), "venue_space_id": venue_space_id}


@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    if user.role == "organizer" and payload.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Organizers can only create events under their own account")
    venue = db.get(Venue, payload.venue_id)
    if not venue or venue.city_id != payload.city_id:
        raise HTTPException(status_code=422, detail="Venue must exist in the selected city")
    if not db.get(EventCategory, payload.category_id):
        raise HTTPException(status_code=404, detail="Event category not found")
    event_data = payload.model_dump()
    event_data["poster_url"] = str(payload.poster_url) if payload.poster_url else None
    item = Event(**event_data)
    db.add(item)
    return save(db, item)


@router.post("/events/{event_id}/publish")
def publish_event(event_id: int, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    item = db.get(Event, event_id)
    if not item:
        raise HTTPException(status_code=404, detail="Event not found")
    if user.role == "organizer" and item.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your event")
    if not db.scalar(select(SessionEvent.id).where(SessionEvent.event_id == event_id)):
        raise HTTPException(status_code=409, detail="Add at least one scheduled session before publishing")
    item.status = "published"
    db.commit()
    db.refresh(item)
    return item


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Session end must be after start")
    if bool(payload.event_id) == bool(payload.movie_id):
        raise HTTPException(status_code=422, detail="Specify exactly one of event_id or movie_id")
    target_id = payload.event_id or payload.movie_id
    target = db.get(Event if payload.event_id else Movie, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Movie or event not found")
    if user.role == "organizer":
        if not payload.event_id or target.organizer_id != user.id:
            raise HTTPException(status_code=403, detail="Organizers can schedule only their own events")
    space = db.get(VenueSpace, payload.venue_space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Venue space not found")
    if payload.event_id and target.venue_id != space.venue_id:
        raise HTTPException(status_code=422, detail="Event sessions must use a space belonging to the event venue")
    if payload.movie_id and space.space_type != "screen":
        raise HTTPException(status_code=422, detail="Movie shows must be scheduled in a cinema screen")
    item = SessionEvent(**payload.model_dump())
    db.add(item)
    return save(db, item)
