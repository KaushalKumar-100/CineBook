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


def test_venue_discovery_routes_are_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/venues" in paths
    assert "/api/v1/venues/{venue_id}" in paths
    assert "/api/v1/venues/{venue_id}/events" in paths


def test_show_seat_inventory_tables_are_registered():
    assert "show_seat_holds" in Base.metadata.tables
    assert "booking_tickets" in Base.metadata.tables


def test_sessions_have_show_specific_pricing_columns():
    columns = set(Base.metadata.tables["sessions"].columns.keys())
    assert {"tax_percent", "convenience_fee"}.issubset(columns)


def test_seats_have_reusable_layout_category():
    assert "seat_category" in Base.metadata.tables["seats"].columns


def test_booking_schema_stores_checkout_breakdown_and_ticket_code():
    booking_columns = set(Base.metadata.tables["bookings"].columns.keys())
    assert {
        "subtotal_amount",
        "tax_amount",
        "convenience_amount",
        "ticket_code",
    }.issubset(booking_columns)


def test_demo_payment_methods_are_explicitly_limited():
    properties = app.openapi()["components"]["schemas"]["BookingCreate"]["properties"]
    assert properties["payment_method"]["enum"] == [
        "demo_upi",
        "demo_card",
        "demo_netbanking",
    ]
    assert properties["payment_method"]["default"] == "demo_upi"
