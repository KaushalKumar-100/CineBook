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
        "demo_upi_qr",
        "demo_card",
        "demo_netbanking",
    ]
    assert properties["payment_method"]["default"] == "demo_upi"


def test_authenticated_seat_hold_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/v1/bookings/holds"]
    assert "delete" in paths["/api/v1/bookings/holds/{session_id}"]


def test_seat_hold_request_schema_limits_selection_size():
    seat_ids = app.openapi()["components"]["schemas"]["SeatHoldCreate"]["properties"]["seat_ids"]
    assert seat_ids["minItems"] == 1
    assert seat_ids["maxItems"] == 20


def test_ticket_qr_endpoint_is_registered_and_returns_png_data_url():
    from base64 import b64decode
    from app.routers.bookings import build_ticket_qr_data_url

    assert "/api/v1/bookings/{booking_id}/ticket/qr" in app.openapi()["paths"]
    data_url = build_ticket_qr_data_url("CINEBOOK-TEST-TICKET-8X4K")
    assert data_url.startswith("data:image/png;base64,")
    image_bytes = b64decode(data_url.split(",", 1)[1])
    assert image_bytes[:8] == bytes.fromhex("89504e470d0a1a0a")


def test_platform_module_tables_are_registered():
    expected = {
        "organizer_applications",
        "password_reset_tokens",
        "notifications",
        "event_reviews",
        "refund_requests",
        "audit_logs",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_portal_and_integration_routes_are_registered():
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/portal/profile",
        "/api/v1/portal/dashboard",
        "/api/v1/portal/organizer-applications",
        "/api/v1/portal/admin/organizer-applications",
        "/api/v1/portal/admin/events/pending",
        "/api/v1/portal/admin/refunds",
        "/api/v1/portal/tickets/check-in",
        "/api/v1/portal/reports/sales",
        "/api/v1/integrations/tmdb/search",
        "/api/v1/integrations/tmdb/import",
        "/api/v1/integrations/ticketmaster/events",
        "/api/v1/integrations/posters",
        "/api/v1/integrations/ai/event-description",
        "/api/v1/auth/password-reset/request",
        "/api/v1/auth/password-reset/confirm",
    }
    assert expected.issubset(set(paths))


def test_sessions_support_general_admission_and_assigned_seating():
    columns = set(Base.metadata.tables["sessions"].columns.keys())
    assert "booking_mode" in columns
    values = app.openapi()["components"]["schemas"]["SessionCreate"]["properties"]["booking_mode"]["enum"]
    assert values == ["assigned", "general_admission"]


def test_ticket_checkin_is_single_use_metadata():
    columns = set(Base.metadata.tables["booking_tickets"].columns.keys())
    assert {"checked_in_at", "checked_in_by"}.issubset(columns)
