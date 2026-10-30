"""Seed local-only CineBook demo data, including one movie and two events.

Run from the backend directory with: python -m scripts.seed_demo
The script prompts for an organizer account and never contains a default password.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
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
    else:
        existing.description = description
        existing.price = price
        existing.capacity = capacity
        existing.is_active = True
        db.flush()



def ensure_movie(
    db, *, title: str, synopsis: str, language: str, duration_minutes: int,
    release_date: datetime, certificate: str, poster_url: str,
) -> Movie:
    movie = db.scalar(select(Movie).where(Movie.title == title))
    if movie is None:
        movie = Movie(title=title, is_active=True)
        db.add(movie)
        db.flush()
    movie.synopsis = synopsis
    movie.language = language
    movie.duration_minutes = duration_minutes
    movie.release_date = release_date
    movie.certificate = certificate
    movie.poster_url = poster_url
    movie.is_active = True
    db.flush()
    return movie


def ensure_event(
    db, *, organizer: User, city: City, category: EventCategory, venue: Venue,
    title: str, description: str, poster_url: str | None = None,
) -> Event:
    event = db.scalar(select(Event).where(Event.title == title))
    if event is None:
        event = Event(
            organizer_id=organizer.id, city_id=city.id, category_id=category.id,
            venue_id=venue.id, title=title, description=description,
            event_type="major", status="published", poster_url=poster_url,
        )
        db.add(event)
        db.flush()
    else:
        event.organizer_id = organizer.id
        event.city_id = city.id
        event.category_id = category.id
        event.venue_id = venue.id
        event.description = description
        event.status = "published"
        event.poster_url = poster_url
    db.flush()
    return event


def ensure_session_at(
    db, *, movie: Movie | None = None, event: Event | None = None,
    space: VenueSpace, starts_at: datetime, duration_minutes: int,
    base_price: Decimal,
) -> SessionEvent:
    session = db.scalar(select(SessionEvent).where(
        SessionEvent.venue_space_id == space.id,
        SessionEvent.movie_id == (movie.id if movie else None),
        SessionEvent.event_id == (event.id if event else None),
        SessionEvent.starts_at == starts_at,
    ))
    if session is None:
        session = SessionEvent(
            movie_id=movie.id if movie else None,
            event_id=event.id if event else None,
            venue_space_id=space.id,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=duration_minutes),
            base_price=base_price,
            tax_percent=Decimal("18.00"),
            convenience_fee=Decimal("25.00"),
            status="scheduled",
        )
        db.add(session)
        db.flush()
    else:
        session.ends_at = starts_at + timedelta(minutes=duration_minutes)
        session.base_price = base_price
        session.tax_percent = Decimal("18.00")
        session.convenience_fee = Decimal("25.00")
        session.status = "scheduled"
    db.flush()
    return session


def ensure_cinema_seats(db, space: VenueSpace) -> None:
    space.capacity = 60
    for row in "ABCDEF":
        category = "Standard" if row in "ABC" else ("Premium" if row in "DE" else "Recliner")
        seat_type = {"Standard": "standard", "Premium": "premium", "Recliner": "recliner"}[category]
        for number in range(1, 11):
            seat = db.scalar(select(Seat).where(
                Seat.venue_space_id == space.id,
                Seat.row_label == row,
                Seat.seat_number == number,
            ))
            if seat is None:
                seat = Seat(
                    venue_space_id=space.id,
                    row_label=row,
                    seat_number=number,
                    seat_type=seat_type,
                    seat_category=category,
                )
                db.add(seat)
            else:
                seat.seat_type = seat_type
                seat.seat_category = category
    db.flush()


def ensure_session_prices(db, session: SessionEvent, *, standard: Decimal = Decimal("180.00")) -> None:
    ensure_ticket_type(db, session, "Standard", "Standard cinema seat", standard, 30)
    ensure_ticket_type(db, session, "Premium", "Premium cinema seat", Decimal("250.00"), 20)
    ensure_ticket_type(db, session, "Recliner", "Recliner seat", Decimal("350.00"), 10)

def main() -> None:
    settings = get_settings()
    if settings.app_env != "development" or not settings.demo_mode:
        raise SystemExit("Demo seeding is allowed only when APP_ENV=development and DEMO_MODE=true.")
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


        # Replace fictional placeholder catalog rows with recognizable titles from
        # the supplied posters. Session times, seats and prices below are local
        # demonstration inventory, not live cinema/organizer availability.
        placeholder_movie = db.scalar(select(Movie).where(Movie.title == "CineBook Sample Movie"))
        if placeholder_movie:
            placeholder_movie.is_active = False
        for old_title in (
            "Guwahati Riverfront Music Evening",
            "Weekend Build and Learn Workshop",
        ):
            old_event = db.scalar(select(Event).where(Event.title == old_title))
            if old_event:
                old_event.status = "cancelled"

        screen = ensure_space(db, cinema, "Screen 1", "screen", 60)
        ensure_cinema_seats(db, screen)
        movie_rows = [
            {
                "title": "Drishyam The Conclusion",
                "synopsis": "The Salgaonkar family tries to protect the secret behind a past killing as new evidence and a determined Crime Branch officer threaten to reopen the case.",
                "language": "Hindi",
                "duration": 150,
                "release": datetime(2026, 10, 2),
                "certificate": "UA16+",
                "poster": "https://imgix.hoyts.com.au/mx/posters/au/drishyam-the-conclusion-3d42e8ed.jpg",
                "days": 1, "hour": 11,
                "base": Decimal("180.00"),
            },
            {
                "title": "Prahaar",
                "synopsis": "Inspired by public prosecutor Ujjwal Nikam, the courtroom drama follows the legal battle after the 26/11 Mumbai attacks and the pursuit of justice against all odds.",
                "language": "Hindi",
                "duration": 141,
                "release": datetime(2026, 10, 16),
                "certificate": "UA16+",
                "poster": "https://www.tribuneindia.com/sortd-service/imaginary/v22-01/jpg/large/high?url=dGhldHJpYnVuZS1zb3J0ZC1wcm8tcHJvZC1zb3J0ZC9tZWRpYTcwOTc4MjgwLTcwNzgtMTFmMS1hZmFlLTJkNzNlMTMwYzExYi5qcGc%3D",
                "days": 1, "hour": 15,
                "base": Decimal("180.00"),
            },
            {
                "title": "Rajini: The Jailer 2",
                "synopsis": "A retired jailer is pulled back into a dangerous underworld conflict when a new threat puts his family and the legacy he built at risk.",
                "language": "Hindi",
                "duration": 165,
                "release": datetime(2026, 10, 15),
                "certificate": "UA16+",
                "poster": "https://m.media-amazon.com/images/M/MV5BYmE0MTFjOTYtMWYxNC00YjFjLTlhNzYtMWQ5ZDEwNjRmYzE1XkEyXkFqcGc%40._V1_.jpg",
                "days": 2, "hour": 12,
                "base": Decimal("180.00"),
            },
            {
                "title": "Nayyi Navelli",
                "synopsis": "A picture-perfect bride brings unexpected joy to a chaotic Meerut household, until her brother-in-law begins to suspect that their blessing may be a witch in disguise.",
                "language": "Hindi",
                "duration": 138,
                "release": datetime(2026, 10, 16),
                "certificate": "UA16+",
                "poster": "https://m.media-amazon.com/images/M/MV5BZmJjYzUyMmYtNDgyNy00MzlkLWE1ZDAtZDFjNzgxYzQxOGY5XkEyXkFqcGc%40._V1_.jpg",
                "days": 2, "hour": 16,
                "base": Decimal("180.00"),
            },
            {
                "title": "Namit Malhotra's Ramayana",
                "synopsis": "The timeless story of Rama and Ravana returns as a large-scale cinematic retelling, following the epic conflict that has shaped generations.",
                "language": "Hindi, Tamil, Telugu, Kannada",
                "duration": 195,
                "release": datetime(2026, 11, 5),
                "certificate": "U",
                "poster": "https://cf-img-a-in.tosshub.com/sites/visualstory/wp/2025/07/ramayanaITG-1751608352043.jpeg?size=%2A%3A900",
                "days": 6, "hour": 10,
                "base": Decimal("220.00"),
            },
        ]
        for row in movie_rows:
            movie = ensure_movie(
                db, title=row["title"], synopsis=row["synopsis"],
                language=row["language"], duration_minutes=row["duration"],
                release_date=row["release"], certificate=row["certificate"],
                poster_url=row["poster"],
            )
            starts_at = (datetime.now() + timedelta(days=row["days"])).replace(
                hour=row["hour"], minute=0, second=0, microsecond=0,
            )
            movie_session = ensure_session_at(
                db, movie=movie, space=screen, starts_at=starts_at,
                duration_minutes=row["duration"], base_price=row["base"],
            )
            ensure_session_prices(db, movie_session)

        # Theatre performance shown in the supplied Bhumika reference poster.
        nagpur = ensure_city(db, "Nagpur", "Maharashtra")
        theatre_category = ensure_category(db, "Theatre", "Stage plays and live performances")
        bhumika_venue = ensure_venue(
            db, nagpur, "Vasantrao Deshpande Hall", "auditorium",
            "Civil Lines, Nagpur, Maharashtra",
        )
        bhumika_space = ensure_space(db, bhumika_venue, "Main Hall", "hall", 400)
        bhumika = ensure_event(
            db, organizer=organizer, city=nagpur, category=theatre_category,
            venue=bhumika_venue, title="Bhumika",
            description=(
                "Marathi drama, approximately 2 hours 10 minutes. Actor Vivek Jayant, "
                "played by Sachin Khedekar, encounters a dream role that challenges his "
                "core and begins to transform him as he inhabits the character. "
                "Age guidance in the supplied listing: 5 years and above. "
                "CineBook preview schedule and ticket inventory; confirm with the organizer."
            ),
            poster_url="https://in.bmscdn.com/events/moviecard/ET00437976.jpg",
        )
        for day in (9, 16, 23, 29):
            show_at = datetime(2026, 11, day, 11, 0)
            if show_at > datetime.now():
                play_session = ensure_session_at(
                    db, event=bhumika, space=bhumika_space, starts_at=show_at,
                    duration_minutes=130, base_price=Decimal("300.00"),
                )
                ensure_ticket_type(db, play_session, "Regular", "Standard theatre admission", Decimal("300.00"), 200)
                ensure_ticket_type(db, play_session, "Premium", "Premium theatre admission", Decimal("450.00"), 120)
                ensure_ticket_type(db, play_session, "VIP", "Front section admission", Decimal("650.00"), 80)

        # A small Mumbai selection based on the BookMyShow events page supplied
        # as a reference. Dates/remaining inventory are seeded demo values.
        mumbai = ensure_city(db, "Mumbai", "Maharashtra")
        music_category = ensure_category(db, "Music Shows", "Live concerts and music performances")
        comedy_category = ensure_category(db, "Comedy Shows", "Stand-up comedy and live humour")
        experience_category = ensure_category(db, "Experiences", "Immersive and interactive experiences")
        mumbai_rows = [
            {
                "title": "The Messi Experience: A Dream Come True",
                "category": experience_category,
                "venue_name": "The Messi Experience, Century Mills",
                "venue_address": "Century Mills, Lower Parel, Mumbai, Maharashtra",
                "venue_type": "convention_center",
                "space_name": "Experience Floor",
                "space_type": "open_area",
                "capacity": 400,
                "date": datetime(2026, 11, 7, 10, 0),
                "duration": 180,
                "price": Decimal("999.00"),
                "premium": Decimal("1499.00"),
                "description": "An immersive football experience celebrating Lionel Messi's career through interactive exhibits and fan-focused installations. Preview schedule and prices are for CineBook testing.",
            },
            {
                "title": "Papa Yaar by Zakir Khan",
                "category": comedy_category,
                "venue_name": "DOME, SVP Stadium",
                "venue_address": "DOME, SVP Stadium, Worli, Mumbai, Maharashtra",
                "venue_type": "auditorium",
                "space_name": "Main Arena",
                "space_type": "hall",
                "capacity": 600,
                "date": datetime(2026, 11, 14, 20, 0),
                "duration": 120,
                "price": Decimal("1299.00"),
                "premium": Decimal("1999.00"),
                "description": "A live stand-up evening with Zakir Khan, built around observational humour, family stories and everyday relationships. Preview schedule and prices are for CineBook testing.",
            },
            {
                "title": "CALVIN HARRIS - Live in Mumbai",
                "category": music_category,
                "venue_name": "Infinity Bay Sewri",
                "venue_address": "Infinity Bay, Sewri, Mumbai, Maharashtra",
                "venue_type": "open_ground",
                "space_name": "Concert Ground",
                "space_type": "open_area",
                "capacity": 1200,
                "date": datetime(2026, 12, 12, 18, 30),
                "duration": 210,
                "price": Decimal("3500.00"),
                "premium": Decimal("5500.00"),
                "description": "A large-scale electronic music night featuring DJ and producer Calvin Harris in Mumbai. Preview schedule and prices are for CineBook testing.",
            },
        ]
        for row in mumbai_rows:
            venue = ensure_venue(
                db, mumbai, row["venue_name"], row["venue_type"], row["venue_address"],
            )
            space = ensure_space(
                db, venue, row["space_name"], row["space_type"], row["capacity"],
            )
            event = ensure_event(
                db, organizer=organizer, city=mumbai, category=row["category"],
                venue=venue, title=row["title"], description=row["description"],
            )
            if row["date"] > datetime.now():
                session = ensure_session_at(
                    db, event=event, space=space, starts_at=row["date"],
                    duration_minutes=row["duration"], base_price=row["price"],
                )
                ensure_ticket_type(db, session, "General Admission", "Standard event entry", row["price"], row["capacity"] * 3 // 4)
                ensure_ticket_type(db, session, "Premium", "Premium event entry", row["premium"], max(1, row["capacity"] // 4))

        # Add five more Indian metro cities to the searchable city directory.
        # These are city records only; do not invent venues or live showtimes.
        additional_cities = [
            ("Delhi", "Delhi"),
            ("Bengaluru", "Karnataka"),
            ("Hyderabad", "Telangana"),
            ("Kolkata", "West Bengal"),
            ("Pune", "Maharashtra"),
        ]
        for city_name, state_name in additional_cities:
            ensure_city(db, city_name, state_name)

        db.commit()
        print("CineBook demo data is ready.")
        print("Created/verified: Guwahati cinema + 60 categorized seats, five movie listings,")
        print("Bhumika theatre dates in Nagpur, and three Mumbai experience listings.")
        print("Added city directory entries: Delhi, Bengaluru, Hyderabad, Kolkata, and Pune.")
        print("All seeded showtimes, seat inventory and prices are demo values.")
        print(f"Organizer account: {organizer.email} (role: {organizer.role})")
        print("Restart the API if it is already running, then refresh the frontend.")
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
