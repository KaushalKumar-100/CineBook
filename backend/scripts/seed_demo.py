"""Seed local-only CineBook demo data, including one movie and two events.

Run from the backend directory with: python -m scripts.seed_demo
The script prompts for an organizer account and never contains a default password.
"""
from datetime import datetime, timedelta
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, SessionLocal, engine
from app.models import (
    City, Event, EventCategory, Movie, Seat, SessionEvent, TicketType,
    User, Venue, VenueSpace,
)
from app.security import hash_password


def ensure_city(db, name: str, state: str) -> City:
    city = db.scalar(select(City).where(City.name == name, City.state == state, City.country == "India"))
    if city is None:
        city = City(name=name, state=state, country="India")
        db.add(city)
        db.flush()
    return city


def ensure_category(db, name: str, description: str) -> EventCategory:
    category = db.scalar(select(EventCategory).where(EventCategory.name == name))
    if category is None:
        category = EventCategory(name=name, description=description)
        db.add(category)
        db.flush()
    return category


def ensure_venue(db, city: City, name: str, venue_type: str, address: str) -> Venue:
    venue = db.scalar(select(Venue).where(Venue.city_id == city.id, Venue.name == name))
    if venue is None:
        venue = Venue(city_id=city.id, name=name, venue_type=venue_type, address=address)
        db.add(venue)
        db.flush()
    return venue


def ensure_space(db, venue: Venue, name: str, space_type: str, capacity: int) -> VenueSpace:
    space = db.scalar(select(VenueSpace).where(VenueSpace.venue_id == venue.id, VenueSpace.name == name))
    if space is None:
        space = VenueSpace(venue_id=venue.id, name=name, space_type=space_type, capacity=capacity)
        db.add(space)
        db.flush()
    return space


def ensure_future_session(db, *, movie=None, event=None, space: VenueSpace, price: float, days_ahead: int) -> SessionEvent:
    now = datetime.now()
    existing = db.scalar(
        select(SessionEvent)
        .where(
            SessionEvent.venue_space_id == space.id,
            SessionEvent.status == "scheduled",
            SessionEvent.starts_at > now,
            SessionEvent.movie_id == (movie.id if movie else None),
            SessionEvent.event_id == (event.id if event else None),
        )
        .order_by(SessionEvent.starts_at)
    )
    if existing:
        return existing
    starts_at = (now + timedelta(days=days_ahead)).replace(hour=18, minute=0, second=0, microsecond=0)
    duration = movie.duration_minutes if movie else 150
    session = SessionEvent(
        movie_id=movie.id if movie else None,
        event_id=event.id if event else None,
        venue_space_id=space.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=duration),
        base_price=price,
        status="scheduled",
    )
    db.add(session)
    db.flush()
    return session


def ensure_ticket_type(db, session: SessionEvent, name: str, description: str, price: float, capacity: int) -> None:
    existing = db.scalar(select(TicketType).where(TicketType.session_id == session.id, TicketType.name == name))
    if existing is None:
        db.add(TicketType(
            session_id=session.id,
            name=name,
            description=description,
            price=price,
            capacity=capacity,
            is_active=True,
        ))
        db.flush()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    display_name = input("Demo organizer display name: ").strip() or "CineBook Demo Organizer"
    email = input("Organizer email (local demo account): ").strip().lower()
    if "@" not in email:
        raise SystemExit("Enter a valid email address.")
    db = SessionLocal()
    try:
        organizer = db.scalar(select(User).where(User.email == email))
        if organizer is None:
            password = getpass("Create a password for this organizer (8+ characters): ")
            confirm = getpass("Confirm password: ")
            if len(password) < 8 or password != confirm:
                raise SystemExit("Passwords must match and contain at least 8 characters.")
            organizer = User(
                name=display_name,
                email=email,
                password_hash=hash_password(password),
                role="organizer",
                is_active=True,
            )
            db.add(organizer)
            db.flush()
        elif organizer.role == "customer":
            promote = input(
                "This account is a customer. Promote it to organizer for this local demo? [y/N]: "
            ).strip().lower()
            if promote != "y":
                raise SystemExit("No account changed. Re-run with another email or explicitly approve promotion.")
            organizer.role = "organizer"
        elif organizer.role not in {"organizer", "admin"}:
            raise SystemExit("The selected account cannot manage events.")
        
        guwahati = ensure_city(db, "Guwahati", "Assam")
        tezpur = ensure_city(db, "Tezpur", "Assam")
        concert_category = ensure_category(db, "Concert", "Live music and concerts")
        workshop_category = ensure_category(db, "Workshop", "Learning and hands-on sessions")

        cinema = ensure_venue(db, guwahati, "CineBook Demo Cinema", "cinema", "Demo Road, Guwahati, Assam")
        cinema_screen = ensure_space(db, cinema, "Screen 1", "screen", 40)
        for row in ("A", "B", "C", "D"):
            for number in range(1, 11):
                seat = db.scalar(select(Seat).where(
                    Seat.venue_space_id == cinema_screen.id,
                    Seat.row_label == row,
                    Seat.seat_number == number,
                ))
                if seat is None:
                    db.add(Seat(venue_space_id=cinema_screen.id, row_label=row, seat_number=number, seat_type="standard"))

        movie = db.scalar(select(Movie).where(Movie.title == "CineBook Sample Movie"))
        if movie is None:
            movie = Movie(
                title="CineBook Sample Movie",
                synopsis="A fictional sample movie used to demonstrate show scheduling and seat booking.",
                language="Hindi",
                duration_minutes=120,
                certificate="U/A",
                poster_url="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba",
                is_active=True,
            )
            db.add(movie)
            db.flush()
        ensure_future_session(db, movie=movie, space=cinema_screen, price=250.00, days_ahead=7)

        concert_venue = ensure_venue(
            db, guwahati, "Brahmaputra Riverside Grounds", "open_ground",
            "Riverside Road, Guwahati, Assam",
        )
        concert_space = ensure_space(db, concert_venue, "Main Area", "open_area", 300)
        concert = db.scalar(select(Event).where(
            Event.organizer_id == organizer.id,
            Event.title == "Guwahati Riverfront Music Evening",
        ))
        if concert is None:
            concert = Event(
                organizer_id=organizer.id,
                city_id=guwahati.id,
                category_id=concert_category.id,
                venue_id=concert_venue.id,
                title="Guwahati Riverfront Music Evening",
                description="A fictional large-format outdoor music event for the CineBook demo.",
                event_type="major",
                status="published",
                poster_url="https://images.unsplash.com/photo-1459749411175-04bf5292ceea",
            )
            db.add(concert)
            db.flush()
        concert_session = ensure_future_session(db, event=concert, space=concert_space, price=299.00, days_ahead=30)
        ensure_ticket_type(db, concert_session, "General Admission", "Standard event entry", 299.00, 300)

        local_venue = ensure_venue(
            db, tezpur, "Tezpur Makerspace", "auditorium",
            "College Road, Tezpur, Assam",
        )
        local_space = ensure_space(db, local_venue, "Workshop Hall", "hall", 80)
        workshop = db.scalar(select(Event).where(
            Event.organizer_id == organizer.id,
            Event.title == "Weekend Build and Learn Workshop",
        ))
        if workshop is None:
            workshop = Event(
                organizer_id=organizer.id,
                city_id=tezpur.id,
                category_id=workshop_category.id,
                venue_id=local_venue.id,
                title="Weekend Build and Learn Workshop",
                description="A fictional local workshop for students and first-time makers.",
                event_type="local",
                status="published",
                poster_url="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
            )
            db.add(workshop)
            db.flush()
        workshop_session = ensure_future_session(db, event=workshop, space=local_space, price=99.00, days_ahead=14)
        ensure_ticket_type(db, workshop_session, "Student Pass", "Student admission", 99.00, 80)

        db.commit()
        print("CineBook demo data is ready.")
        print("Created/verified: Guwahati and Tezpur, demo cinema + 40 seats, one sample movie,")
        print("one major concert, one local workshop, sessions, and ticket types.")
        print(f"Organizer account: {organizer.email} (role: {organizer.role})")
        print("Restart the API if it is already running, then refresh the frontend.")
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
