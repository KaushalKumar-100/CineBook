from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=30)

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    country: str = Field(default="India", max_length=100)

class VenueCreate(BaseModel):
    city_id: int
    name: str = Field(min_length=2, max_length=200)
    venue_type: str = "other"
    address: str = Field(min_length=3, max_length=500)
    contact_number: str | None = Field(default=None, max_length=30)

class VenueSpaceCreate(BaseModel):
    venue_id: int
    name: str = Field(min_length=1, max_length=150)
    space_type: str = "other"
    capacity: int = Field(gt=0, le=1_000_000)

class MovieCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    synopsis: str | None = None
    language: str = Field(default="Hindi", max_length=60)
    duration_minutes: int = Field(gt=0, le=1000)
    release_date: datetime | None = None
    certificate: str | None = Field(default=None, max_length=20)
    poster_url: HttpUrl | None = None

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)

class EventCreate(BaseModel):
    organizer_id: int
    city_id: int
    category_id: int
    venue_id: int
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    event_type: str = "local"
    poster_url: HttpUrl | None = None

class SessionCreate(BaseModel):
    event_id: int | None = None
    movie_id: int | None = None
    venue_space_id: int
    starts_at: datetime
    ends_at: datetime
    base_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    tax_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100, max_digits=5, decimal_places=2)
    convenience_fee: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)

class TicketTypeCreate(BaseModel):
    session_id: int
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    capacity: int = Field(gt=0, le=1_000_000)

class BookingCreate(BaseModel):
    session_id: int
    ticket_type_id: int | None = None
    quantity: int = Field(default=1, ge=1, le=20)
    seat_ids: list[int] | None = Field(default=None, max_length=20)

class SeatHoldCreate(BaseModel):
    session_id: int
    seat_ids: list[int] = Field(min_length=1, max_length=10)

class SeatCategoryPriceCreate(BaseModel):
    seat_category: str = Field(min_length=1, max_length=40)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

class PaymentVerify(BaseModel):
    razorpay_order_id: str = Field(min_length=5, max_length=100)
    razorpay_payment_id: str = Field(min_length=5, max_length=100)
    razorpay_signature: str = Field(min_length=20, max_length=256)

class BookingOut(BaseModel):
    id: int
    booking_reference: str
    session_id: int
    status: str
    total_amount: Decimal
    subtotal_amount: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    convenience_amount: Decimal = Decimal("0.00")
    expires_at: datetime | None = None
    ticket_code: str | None = None
    model_config = ConfigDict(from_attributes=True)

class PaymentOut(BaseModel):
    id: int
    booking_id: int
    provider: str
    provider_reference: str | None
    amount: Decimal
    status: str
    model_config = ConfigDict(from_attributes=True)


class BookingQuote(BaseModel):
    session_id: int
    seat_lines: list[dict]
    subtotal: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    convenience_fee: Decimal
    total_amount: Decimal
