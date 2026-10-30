from app.main import app
from app.models import Base


def test_core_database_tables_are_registered():
    expected = {
        "users",
        "cities",
        "venues",
        "venue_spaces",
        "movies",
        "event_categories",
        "events",
        "sessions",
        "seats",
        "ticket_types",
        "bookings",
        "booking_items",
        "payments",
        "show_seat_holds",
        "booking_tickets",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_expected_api_routes_are_registered():
    paths = set(app.openapi()["paths"])
    expected = {
        "/health/db",
        "/health/schema",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/cities",
        "/api/v1/movies",
        "/api/v1/events",
        "/api/v1/sessions",
        "/api/v1/sessions/{session_id}/availability",
        "/api/v1/bookings",
        "/api/v1/bookings/me",
        "/api/v1/manage/ticket-types",
        "/api/v1/manage/seats/bulk",
    }
    assert expected.issubset(paths)
