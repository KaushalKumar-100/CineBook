from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(Enum("customer", "organizer", "admin", name="user_role"), default="customer", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")

class City(Base):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("name", "state", "country", name="uq_city_location"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)

class Venue(TimestampMixin, Base):
    __tablename__ = "venues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    venue_type: Mapped[str] = mapped_column(Enum("cinema", "auditorium", "stadium", "open_ground", "convention_center", "club", "other", name="venue_type"), default="other", nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    contact_number: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    city: Mapped[City] = relationship()

class VenueSpace(Base):
    __tablename__ = "venue_spaces"
    __table_args__ = (UniqueConstraint("venue_id", "name", name="uq_venue_space_name"), CheckConstraint("capacity > 0", name="ck_venue_space_capacity"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    space_type: Mapped[str] = mapped_column(Enum("screen", "hall", "stage", "open_area", "other", name="space_type"), default="other", nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    venue: Mapped[Venue] = relationship()

class Movie(TimestampMixin, Base):
    __tablename__ = "movies"
    __table_args__ = (CheckConstraint("duration_minutes > 0", name="ck_movie_duration"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    synopsis: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(60), default="Hindi", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime)
    certificate: Mapped[str | None] = mapped_column(String(20))
    poster_url: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class EventCategory(Base):
    __tablename__ = "event_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

class Event(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_city_status", "city_id", "status"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("event_categories.id", ondelete="RESTRICT"), nullable=False)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Enum("local", "major", name="event_type"), default="local", nullable=False)
    status: Mapped[str] = mapped_column(Enum("draft", "pending_approval", "published", "cancelled", "completed", "rejected", name="event_status"), default="draft", nullable=False, index=True)
    poster_url: Mapped[str | None] = mapped_column(String(1000))
    organizer: Mapped[User] = relationship()
    city: Mapped[City] = relationship()
    category: Mapped[EventCategory] = relationship()
    venue: Mapped[Venue] = relationship()
    sessions: Mapped[list["SessionEvent"]] = relationship(back_populates="event", cascade="all, delete-orphan")

class SessionEvent(Base):
    __tablename__ = "sessions"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="ck_session_time"), CheckConstraint("base_price >= 0", name="ck_session_price"), CheckConstraint("(event_id IS NOT NULL AND movie_id IS NULL) OR (event_id IS NULL AND movie_id IS NOT NULL)", name="ck_session_target"), Index("ix_sessions_start", "starts_at"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[int | None] = mapped_column(ForeignKey("movies.id", ondelete="RESTRICT"), index=True)
    venue_space_id: Mapped[int] = mapped_column(ForeignKey("venue_spaces.id", ondelete="RESTRICT"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    convenience_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    booking_mode: Mapped[str] = mapped_column(Enum("assigned", "general_admission", name="session_booking_mode"), default="general_admission", nullable=False)
    status: Mapped[str] = mapped_column(Enum("scheduled", "cancelled", "completed", name="session_status"), default="scheduled", nullable=False)
    event: Mapped[Event | None] = relationship(back_populates="sessions")
    movie: Mapped[Movie | None] = relationship()
    venue_space: Mapped[VenueSpace] = relationship()

class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("venue_space_id", "row_label", "seat_number", name="uq_seat_position"), CheckConstraint("seat_number > 0", name="ck_seat_number"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venue_space_id: Mapped[int] = mapped_column(ForeignKey("venue_spaces.id", ondelete="RESTRICT"), nullable=False, index=True)
    row_label: Mapped[str] = mapped_column(String(10), nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_type: Mapped[str] = mapped_column(Enum("standard", "premium", "recliner", name="seat_type"), default="standard", nullable=False)
    seat_category: Mapped[str] = mapped_column(String(40), default="Standard", nullable=False)

class TicketType(Base):
    __tablename__ = "ticket_types"
    __table_args__ = (CheckConstraint("price >= 0", name="ck_ticket_price"), CheckConstraint("capacity > 0", name="ck_ticket_capacity"), UniqueConstraint("session_id", "name", name="uq_ticket_type_session_name"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_reference: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(Enum("pending", "confirmed", "cancelled", "expired", name="booking_status"), default="pending", nullable=False, index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    convenience_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    ticket_code: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    user: Mapped[User] = relationship(back_populates="bookings")
    session: Mapped[SessionEvent] = relationship()
    items: Mapped[list["BookingItem"]] = relationship(back_populates="booking", cascade="all, delete-orphan")

class BookingItem(Base):
    __tablename__ = "booking_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_booking_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_booking_unit_price"),
        CheckConstraint("(seat_id IS NOT NULL AND ticket_type_id IS NULL AND quantity = 1) OR (seat_id IS NULL AND ticket_type_id IS NOT NULL)", name="ck_booking_allocation"),
        UniqueConstraint("booking_id", "seat_id", name="uq_booking_seat_once"),
        Index("ix_booking_items_seat", "seat_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_type_id: Mapped[int | None] = mapped_column(ForeignKey("ticket_types.id", ondelete="RESTRICT"))
    seat_id: Mapped[int | None] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    booking: Mapped[Booking] = relationship(back_populates="items")
    ticket_type: Mapped[TicketType | None] = relationship()
    seat: Mapped[Seat | None] = relationship()

class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(60), default="demo", nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(150), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(Enum("initiated", "succeeded", "failed", "refunded", name="payment_status"), default="initiated", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)


class ShowSeatHold(Base):
    """A temporary lock for one physical seat on one show.

    The same seat can be used by other shows; the uniqueness is session-scoped.
    """
    __tablename__ = "show_seat_holds"
    __table_args__ = (
        UniqueConstraint("session_id", "seat_id", name="uq_show_seat_hold"),
        Index("ix_show_seat_holds_expiry", "expires_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class BookingTicket(Base):
    """QR-ticket token issued only after a booking is confirmed."""
    __tablename__ = "booking_tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    ticket_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    checked_in_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))



class OrganizerApplication(TimestampMixin, Base):
    __tablename__ = "organizer_applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    organization_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Enum("pending", "approved", "rejected", name="organizer_application_status"), default="pending", nullable=False, index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_note: Mapped[str | None] = mapped_column(String(1000))
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), default="info", nullable=False)
    link: Mapped[str | None] = mapped_column(String(500))
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class EventReview(TimestampMixin, Base):
    __tablename__ = "event_reviews"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_review_user"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_event_review_rating"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, unique=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000))
    user: Mapped[User] = relationship()
    event: Mapped[Event] = relationship()


class RefundRequest(TimestampMixin, Base):
    __tablename__ = "refund_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(Enum("requested", "approved", "rejected", "processed", name="refund_request_status"), default="requested", nullable=False, index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolution_note: Mapped[str | None] = mapped_column(String(1000))
    booking: Mapped[Booking] = relationship()
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    details: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
