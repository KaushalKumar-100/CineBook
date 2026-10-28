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
- Responsive frontend with search/filtering, seat/ticket selection, and booking integration.

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
4. From `backend/`, run `python -m scripts.seed_demo` and follow the prompts. The script creates an organizer account and sample movie/concert/workshop data.
5. Start the API from `backend/` with `uvicorn app.main:app --reload`; open http://127.0.0.1:8000/docs.
6. Open a second terminal, run `cd frontend`, `npm install`, and `npm run dev`. Open the URL printed by Vite (normally http://localhost:5173).

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for full instructions.

## Important
- Event and movie examples are fictional coursework data.
- Payment and refund entries are simulated; no real payment gateway or card data is used.
- `DEMO_MODE=true` enables local development table creation; keep the `.env` file private and do not use demo configuration in production.
- Run `pytest` from `backend/`; GitHub Actions checks backend tests and builds the frontend.
