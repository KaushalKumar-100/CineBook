# CineBook

CineBook is a DBMS-focused ticket-booking platform inspired by BookMyShow. It supports cinema shows, major events, and local experiences such as concerts, festivals, college fests, workshops, comedy events, and community activities.

## Stack
- Frontend: React + Vite
- Backend: Python + FastAPI
- ORM/database access: SQLAlchemy 2 + PyMySQL
- Database: MySQL 8+
- Authentication: JWT bearer tokens and Argon2 password hashing
- Tests: pytest + GitHub Actions

## Features
- Customer registration, sign-in, password hashing, JWT authentication, and role checks.
- Cities, venues, screens/spaces, movies, event categories, events, and scheduled sessions.
- Discovery by title, city, category, event type, and session.
- Numbered cinema seats and capacity-limited general-admission tickets.
- Booking history, cancellation, and simulated payment/refund records.
- Full MySQL DDL, repeatable SQL seed data, and an interactive major/local event demo seeder.
- BookMyShow-inspired discovery, venue/showtime selection, price-tiered seat maps, temporary seat holds, a simulated payment gateway with UPI QR display and success/decline test paths, booking confirmation, booking history, and printable QR e-tickets.

## Quick start (Windows)
1. Run `backend/sql/schema.sql` in MySQL Workbench.
2. In PowerShell, create the backend environment:
   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```
3. Edit `backend/.env` locally. Set the MySQL credentials and a long random `SECRET_KEY`. Never commit or share `.env`.
4. For an existing database, back it up and run `backend/sql/migrations/002_venue_booking_flow.sql` in MySQL Workbench before seeding. From `backend/`, run `python -m scripts.seed_demo` and follow the prompts. The script creates an organizer account, five movie listings, cinema seats in three price categories, Bhumika at Vasantrao Deshpande Hall in Nagpur, sample Mumbai experiences, and five additional city-directory records: Delhi, Bengaluru, Hyderabad, Kolkata, and Pune.
5. Start the API from `backend/` with `uvicorn app.main:app --reload`; open http://127.0.0.1:8000/docs.
6. Open a second terminal, run `cd frontend`, `npm install`, and `npm run dev`. Open the URL printed by Vite (normally http://localhost:5173).

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for full instructions.

## Important
- Movie and play titles/descriptions are based on the supplied sample posters and public listing descriptions. All seeded show dates, seat inventory, ticket rates, tax and convenience charges are demonstration values and must not be treated as live venue availability.
- Checkout opens a clearly labelled simulated UPI/card/netbanking gateway with success and decline test actions. No payment provider is called, no money is collected, and no card, UPI PIN, CVV or OTP data is requested. Successful demo checkout generates a random ticket reference and downloadable QR code; the QR stores only that reference and is not valid for real-venue entry.
- `DEMO_MODE=true` enables local development table creation; keep the `.env` file private and do not use demo configuration in production.
- Run `pytest` from `backend/`; GitHub Actions checks backend tests and builds the frontend.


## Production-readiness notes

The project is a strong local/demo foundation, but a public ticketing service needs the following before accepting real customers or money:

- Set `APP_ENV=production`, `DEMO_MODE=false`, a unique random `SECRET_KEY` (at least 32 characters), real database credentials, and `CORS_ALLOWED_ORIGINS` to the exact deployed frontend origin.
- The production API hides Swagger/OpenAPI endpoints; keep API docs enabled only in trusted development environments.
- Use managed MySQL with backups, TLS, least-privilege database credentials, monitoring, and a versioned migration tool such as Alembic before schema changes.
- Add a real payment provider with signed webhook verification and idempotency before taking payments. Current payment/refund records are explicitly simulated.
- Configure HTTPS, rate limiting, request logging/monitoring, and a reviewed privacy/retention policy at the deployment/edge layer.
- Build and test both services in CI; verify concurrency and booking rollback behavior against the same MySQL engine/version used in production.

The frontend now includes locally generated SVG poster artwork for movies, concerts, comedy, campus events, workshops, and general experiences. These local posters are reliable fallback artwork; listing-specific external poster URLs remain optional.


For the optional merchant UPI QR display, place your own valid merchant QR image at `frontend/public/payment-qr.png`. Scanning a static QR happens outside CineBook and cannot be verified by this demo app; the confirmation button remains simulated.
