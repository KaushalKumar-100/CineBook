# CineBook Backend

## Requirements
Python 3.11+, MySQL 8+, and MySQL Workbench.

## Local Windows setup
Run in PowerShell from the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` locally. Set your MySQL user/password and replace `SECRET_KEY` with a long random secret. Keep `.env` private.

Create the database by running `backend/sql/schema.sql` in MySQL Workbench (it creates `cinebook_db` and the current tables). For an existing CineBook database, first take a backup and then run `backend/sql/migrations/002_venue_booking_flow.sql` to add the venue/show booking fields and inventory tables without deleting demo data. The optional `backend/sql/seed_demo.sql` adds cities, categories, a demo cinema, one sample movie, 40 seats, and a future show. For the complete sample including a major concert and local workshop, use the interactive Python seeder below after configuring `.env`.

Run the local-only demo seeder from `backend/` (it creates missing tables and prompts for an organizer email/password; no default credentials are stored in the project):

```powershell
python -m scripts.seed_demo
```

Then start the API from `backend/`:

```powershell
uvicorn app.main:app --reload
```

URLs:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health/db
- http://127.0.0.1:8000/health/schema

For local coursework, missing tables are auto-created only when `APP_ENV=development` and `DEMO_MODE=true`. Disable this mode outside local development. The versioned SQL migration is the source of truth for upgrading an existing database.

## API reference
### Authentication
- `POST /api/v1/auth/register`: create customer account.
- `POST /api/v1/auth/login`: form fields `username` (email) and `password`; returns bearer token.
- `GET /api/v1/auth/me`: current user.

### Public discovery
- `GET /api/v1/cities`
- `GET /api/v1/venues?city_id=1&q=stadium&venue_type=stadium` — city-scoped venue search
- `GET /api/v1/venues/{venue_id}` — venue details and capacity summary
- `GET /api/v1/venues/{venue_id}/events?category_id=1&sort=date` — published upcoming events at that venue only
- `GET /api/v1/venues/{venue_id}/spaces`
- `GET /api/v1/movies?q=film`
- `GET /api/v1/events?city_id=1&event_type=local&q=music`
- `GET /api/v1/event-categories`
- `GET /api/v1/sessions?event_id=1` or `?movie_id=1`
- `GET /api/v1/sessions/{id}/availability` — returns seats and/or remaining general-admission ticket capacity

### Organizer/admin
- `POST /api/v1/manage/cities` (admin)
- `POST /api/v1/manage/venues` (admin only; no venue ownership table is currently modeled)
- `POST /api/v1/manage/venue-spaces` (admin/organizer; organizers must manage an event at the venue)
- `POST /api/v1/manage/movies` (admin)
- `POST /api/v1/manage/event-categories` (admin)
- `POST /api/v1/manage/events` (admin/organizer)
- `POST /api/v1/manage/events/{id}/publish` (owner organizer/admin)
- `POST /api/v1/manage/sessions` (admin/organizer)
- `POST /api/v1/manage/ticket-types` (admin/organizer; event general admission)
- `POST /api/v1/manage/seats/bulk?venue_space_id=1&seats_per_row=10` with a JSON array of row labels as the body

### Booking (login required)
- `POST /api/v1/bookings`: assigned seats: `{"session_id":1,"seat_ids":[1,2]}`; general admission: `{"session_id":2,"ticket_type_id":1,"quantity":2}`.
- `GET /api/v1/bookings/me`
- `GET /api/v1/bookings/{id}`
- `GET /api/v1/bookings/{id}/payments`
- `POST /api/v1/bookings/{id}/cancel`

Payments/refunds are simulated for coursework. No card information is collected and no real payment provider is connected.

## Create first administrator
Register your own account via `POST /api/v1/auth/register`. Then, using your local MySQL Workbench and after confirming the email, promote only your own account:
```sql
UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';
```
Do not expose an unauthenticated admin creation endpoint.

## Tests
From `backend/` run `pytest`. GitHub Actions also runs backend tests and a frontend production build. Since your MySQL instance is local to your laptop, confirm integration using `/health/db`, `/health/schema`, and Swagger at `/docs` after running the API.

## Database concepts
The project demonstrates normalization, PK/FK relationships, unique constraints, check constraints, role-based access, transaction boundaries, and booking-capacity checks.


## Venue / show booking schema extension

- `sessions.tax_percent` and `sessions.convenience_fee` hold show-specific checkout settings.
- `seats.seat_category` describes a physical seat category while the seat remains part of a venue space's reusable layout.
- `show_seat_holds` scopes temporary locks to one session + physical seat, so the same seat can be sold again for another show.
- `bookings` stores backend-calculated subtotal, tax, convenience fees, expiry, and optional ticket code.
- `booking_tickets` stores issued ticket codes separately from seat inventory.

The discovery endpoints are database-backed. Venue poster/image URLs are not yet stored in the venue model, so the venue API currently returns an empty `images` list rather than inventing URLs.
