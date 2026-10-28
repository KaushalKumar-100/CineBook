-- Readable initial schema overview for DBMS review.
-- The complete set of tables is defined in app/models.py.
-- For local coursework, start the API with APP_ENV=development and DEMO_MODE=true
-- to create missing tables, or use SQLAlchemy Base.metadata.create_all.
CREATE DATABASE IF NOT EXISTS cinebook_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cinebook_db;

-- The ORM is the canonical complete schema for this release.
-- Main entities: users, cities, venues, venue_spaces, movies, event_categories,
-- events, sessions, seats, ticket_types, bookings, booking_items, payments.
-- See app/models.py for all column definitions, foreign keys, check/unique constraints,
-- and indexes. Never store credentials in SQL files.
