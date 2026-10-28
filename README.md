# CineBook

CineBook is a DBMS-focused ticket-booking platform inspired by BookMyShow. It supports cinema shows, major events and local experiences such as concerts, festivals, college fests, workshops, comedy events, and community activities.

## Stack
Python 3.11+, FastAPI, SQLAlchemy 2, MySQL 8+, PyMySQL, JWT bearer authentication, Argon2 password hashing, pytest.

## Quick start (Windows)
1. Create `cinebook_db` in MySQL Workbench:
   ```sql
   CREATE DATABASE IF NOT EXISTS cinebook_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. In PowerShell:
   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```
3. Edit `backend/.env` locally. Set MySQL credentials and replace `SECRET_KEY`. Never commit or share `.env`.
4. Run from `backend/`: `uvicorn app.main:app --reload`.
5. Open http://127.0.0.1:8000/docs.

## Features
- Customer registration, secure password hashing, JWT login, and role checks.
- Cities, venues, venue spaces/screens, movies, event categories, events, and scheduled sessions.
- Discovery and filtering by city, category, type, title, and session.
- Numbered-seat bookings and capacity-limited general admission.
- Booking history, cancellation, and simulated payment/refund records.
- SQLAlchemy relational model with keys, indexes, unique constraints, and check constraints.

See [backend/README.md](backend/README.md) for API details and local setup.

**Payments are simulated only.** No real payment provider or card data is used. The DBMS/API foundation is implemented; frontend UI and deployment are not included in this backend-only repository.
