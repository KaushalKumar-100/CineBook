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
    item = City(name=payload.name.strip(), state=payload.state.strip(), country=payload.country.strip())
    db.add(item)
    return save(db, item)

@router.post("/venues", status_code=status.HTTP_201_CREATED)
def create_venue(payload: VenueCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    item = Venue(**payload.model_dump())
    db.add(item)
    return save(db, item)

@router.post("/venue-spaces", status_code=status.HTTP_201_CREATED)
def create_space(payload: VenueSpaceCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    item = VenueSpace(**payload.model_dump())
    db.add(item)
    return save(db, item)

@router.post("/movies", status_code=status.HTTP_201_CREATED)
def create_movie(payload: MovieCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    item = Movie(**payload.model_dump())
    db.add(item)
    return save(db, item)

@router.post("/event-categories", status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    item = EventCategory(**payload.model_dump())
    db.add(item)
    return save(db, item)

@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    if user.role == "organizer" and payload.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Organizers can only create events under their own account")
    item = Event(**payload.model_dump())
    db.add(item)
    return save(db, item)

@router.post("/events/{event_id}/publish")
def publish_event(event_id: int, db: DbSession, user: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    item = db.get(Event, event_id)
    if not item:
        raise HTTPException(status_code=404, detail="Event not found")
    if user.role == "organizer" and item.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your event")
    item.status = "published"
    db.commit()
    db.refresh(item)
    return item

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: DbSession, _: Annotated[User, Depends(require_roles("admin", "organizer"))]):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Session end must be after start")
    if bool(payload.event_id) == bool(payload.movie_id):
        raise HTTPException(status_code=422, detail="Specify exactly one of event_id or movie_id")
    target_id = payload.event_id or payload.movie_id
    if not db.get(Event if payload.event_id else Movie, target_id):
        raise HTTPException(status_code=404, detail="Movie or event not found")
    if not db.get(VenueSpace, payload.venue_space_id):
        raise HTTPException(status_code=404, detail="Venue space not found")
    item = SessionEvent(**payload.model_dump())
    db.add(item)
    return save(db, item)
