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

Create the database in Workbench:

```sql
CREATE DATABASE IF NOT EXISTS cinebook_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Start in `backend/`:

```powershell
uvicorn app.main:app --reload
```

URLs:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health/db
- http://127.0.0.1:8000/health/schema

For local coursework, missing tables are auto-created only when `APP_ENV=development` and `DEMO_MODE=true`. Disable this mode in other environments and use versioned migrations.

## API reference
### Authentication
- `POST /api/v1/auth/register`: create customer account.
- `POST /api/v1/auth/login`: form fields `username` (email) and `password`; returns bearer token.
- `GET /api/v1/auth/me`: current user.

### Public discovery
- `GET /api/v1/cities`
- `GET /api/v1/venues?city_id=1`
- `GET /api/v1/venues/{venue_id}/spaces`
- `GET /api/v1/movies?q=film`
- `GET /api/v1/events?city_id=1&event_type=local&q=music`
- `GET /api/v1/event-categories`
- `GET /api/v1/sessions?event_id=1` or `?movie_id=1`

### Organizer/admin
- `POST /api/v1/manage/cities` (admin)
- `POST /api/v1/manage/venues` (admin/organizer)
- `POST /api/v1/manage/venue-spaces` (admin/organizer)
- `POST /api/v1/manage/movies` (admin)
- `POST /api/v1/manage/event-categories` (admin)
- `POST /api/v1/manage/events` (admin/organizer)
- `POST /api/v1/manage/events/{id}/publish` (owner organizer/admin)
- `POST /api/v1/manage/sessions` (admin/organizer)

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
From `backend/` run `pytest`. Integration checks against MySQL should also be carried out locally using health endpoints and Swagger docs.

## Database concepts
The project demonstrates normalization, PK/FK relationships, unique constraints, check constraints, role-based access, transaction boundaries, and booking-capacity checks.
