from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.dependencies import DbSession
from app.models import City, Event, EventCategory, Movie, SessionEvent, Venue, VenueSpace

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
    return db.scalars(stmt).unique().all()


@router.get("/event-categories")
def list_categories(db: DbSession):
    return db.scalars(select(EventCategory).order_by(EventCategory.name)).all()


@router.get("/sessions")
def list_sessions(
    db: DbSession,
    event_id: int | None = None,
    movie_id: int | None = None,
    from_time: datetime | None = None,
):
    stmt = select(SessionEvent).where(SessionEvent.status == "scheduled").order_by(SessionEvent.starts_at)
    if event_id is not None:
        stmt = stmt.where(SessionEvent.event_id == event_id)
    if movie_id is not None:
        stmt = stmt.where(SessionEvent.movie_id == movie_id)
    if from_time:
        stmt = stmt.where(SessionEvent.starts_at >= from_time)
    return db.scalars(stmt).all()
