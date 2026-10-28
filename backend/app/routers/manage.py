from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, require_roles
from app.models import City, Event, EventCategory, Movie, SessionEvent, User, Venue, VenueSpace
from app.schemas import CategoryCreate, CityCreate, EventCreate, MovieCreate, SessionCreate, VenueCreate, VenueSpaceCreate

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
    city = City(name=payload.name.strip(), state=payload.state.strip(), country=payload.country.strip())
    db.add(city)
    return save(db, city)


@router.post("/venues", status_code=status.HTTP_201_CREATED)
def create_venue(payload: VenueCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    venue = Venue(**payload.model_dump())
    db.add(venue)
    return save(db, venue)


@router.post("/venue-spaces", status_code=status.HTTP_201_CREATED)
def create_space(payload: VenueSpaceCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    space = VenueSpace(**payload.model_dump())
    db.add(space)
    return save(db, space)


@router.post("/movies", status_code=status.HTTP_201_CREATED)
def create_movie(payload: MovieCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    movie = Movie(**payload.model_dump(mode="python"))
    db.add(movie)
    return save(db, movie)


@router.post("/event-categories", status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    category = EventCategory(**payload.model_dump())
    db.add(category)
    return save(db, category)


@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    if user.role == "organizer" and payload.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Organizers can only create events under their own account")
    event = Event(**payload.model_dump(mode="python"))
    db.add(event)
    return save(db, event)


@router.post("/events/{event_id}/publish")
def publish_event(event_id: int, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if user.role == "organizer" and event.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your event")
    event.status = "published"
    db.commit()
    db.refresh(event)
    return event


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Session end must be after start")
    if bool(payload.event_id) == bool(payload.movie_id):
        raise HTTPException(status_code=422, detail="Specify exactly one of event_id or movie_id")
    target = Event if payload.event_id else Movie
    target_id = payload.event_id or payload.movie_id
    if not db.get(target, target_id):
        raise HTTPException(status_code=404, detail="Movie or event not found")
    if not db.get(VenueSpace, payload.venue_space_id):
        raise HTTPException(status_code=404, detail="Venue space not found")
    session = SessionEvent(**payload.model_dump())
    db.add(session)
    return save(db, session)
