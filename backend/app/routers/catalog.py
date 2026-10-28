from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.dependencies import DbSession
from app.models import City, Event, EventCategory, Movie, SessionEvent, Venue, VenueSpace

router = APIRouter(tags=["Discovery"])

@router.get("/cities")
def list_cities(db: DbSession):
    return db.scalars(select(City).order_by(City.name)).all()

@router.get("/venues")
def list_venues(city_id: int | None = None, db: DbSession = Depends(get_db)):
    stmt = select(Venue).where(Venue.is_active.is_(True)).options(joinedload(Venue.city)).order_by(Venue.name)
    if city_id:
        stmt = stmt.where(Venue.city_id == city_id)
    return db.scalars(stmt).unique().all()

@router.get("/venues/{venue_id}/spaces")
def venue_spaces(venue_id: int, db: DbSession):
    if not db.get(Venue, venue_id):
        raise HTTPException(status_code=404, detail="Venue not found")
    return db.scalars(select(VenueSpace).where(VenueSpace.venue_id == venue_id).order_by(VenueSpace.name)).all()

@router.get("/movies")
def list_movies(q: str | None = Query(default=None, max_length=120), db: DbSession = Depends(get_db)):
    stmt = select(Movie).where(Movie.is_active.is_(True)).order_by(Movie.title)
    if q:
        stmt = stmt.where(Movie.title.ilike(f"%{q}%"))
    return db.scalars(stmt).all()

@router.get("/events")
def list_events(city_id: int | None = None, category_id: int | None = None,
    event_type: str | None = Query(default=None, pattern="^(local|major)$"),
    q: str | None = Query(default=None, max_length=120), db: DbSession = Depends(get_db)):
    stmt = select(Event).where(Event.status == "published").options(
        joinedload(Event.city), joinedload(Event.venue), joinedload(Event.category)
    ).order_by(Event.created_at.desc())
    if city_id:
        stmt = stmt.where(Event.city_id == city_id)
    if category_id:
        stmt = stmt.where(Event.category_id == category_id)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if q:
        stmt = stmt.where(Event.title.ilike(f"%{q}%"))
    return db.scalars(stmt).unique().all()

@router.get("/event-categories")
def list_categories(db: DbSession):
    return db.scalars(select(EventCategory).order_by(EventCategory.name)).all()

@router.get("/sessions")
def list_sessions(event_id: int | None = None, movie_id: int | None = None,
    from_time: datetime | None = None, db: DbSession = Depends(get_db)):
    stmt = select(SessionEvent).where(SessionEvent.status == "scheduled").order_by(SessionEvent.starts_at)
    if event_id:
        stmt = stmt.where(SessionEvent.event_id == event_id)
    if movie_id:
        stmt = stmt.where(SessionEvent.movie_id == movie_id)
    if from_time:
        stmt = stmt.where(SessionEvent.starts_at >= from_time)
    return db.scalars(stmt).all()
