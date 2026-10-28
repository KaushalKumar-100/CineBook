-- CineBook relational schema (MySQL 8+).
-- Run this script after selecting your local MySQL connection in Workbench.
-- Safe to rerun: existing tables are preserved by CREATE TABLE IF NOT EXISTS.
CREATE DATABASE IF NOT EXISTS cinebook_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cinebook_db;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  phone VARCHAR(30) NULL,
  role ENUM('customer','organizer','admin') NOT NULL DEFAULT 'customer',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cities (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  state VARCHAR(100) NOT NULL,
  country VARCHAR(100) NOT NULL DEFAULT 'India',
  CONSTRAINT uq_city_location UNIQUE (name, state, country)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS venues (
  id INT AUTO_INCREMENT PRIMARY KEY,
  city_id INT NOT NULL,
  name VARCHAR(200) NOT NULL,
  venue_type ENUM('cinema','auditorium','stadium','open_ground','convention_center','club','other') NOT NULL DEFAULT 'other',
  address VARCHAR(500) NOT NULL,
  contact_number VARCHAR(30) NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_venues_city_id (city_id),
  CONSTRAINT fk_venues_city FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS venue_spaces (
  id INT AUTO_INCREMENT PRIMARY KEY,
  venue_id INT NOT NULL,
  name VARCHAR(150) NOT NULL,
  space_type ENUM('screen','hall','stage','open_area','other') NOT NULL DEFAULT 'other',
  capacity INT NOT NULL,
  CONSTRAINT uq_venue_space_name UNIQUE (venue_id, name),
  CONSTRAINT ck_venue_space_capacity CHECK (capacity > 0),
  INDEX ix_venue_spaces_venue_id (venue_id),
  CONSTRAINT fk_spaces_venue FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  synopsis TEXT NULL,
  language VARCHAR(60) NOT NULL DEFAULT 'Hindi',
  duration_minutes INT NOT NULL,
  release_date DATETIME NULL,
  certificate VARCHAR(20) NULL,
  poster_url VARCHAR(1000) NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT ck_movie_duration CHECK (duration_minutes > 0),
  INDEX ix_movies_title (title)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS event_categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(500) NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  organizer_id INT NOT NULL,
  city_id INT NOT NULL,
  category_id INT NOT NULL,
  venue_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT NULL,
  event_type ENUM('local','major') NOT NULL DEFAULT 'local',
  status ENUM('draft','published','cancelled','completed') NOT NULL DEFAULT 'draft',
  poster_url VARCHAR(1000) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_events_organizer_id (organizer_id),
  INDEX ix_events_city_id (city_id),
  INDEX ix_events_city_status (city_id, status),
  INDEX ix_events_title (title),
  INDEX ix_events_status (status),
  CONSTRAINT fk_events_organizer FOREIGN KEY (organizer_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_events_city FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE RESTRICT,
  CONSTRAINT fk_events_category FOREIGN KEY (category_id) REFERENCES event_categories(id) ON DELETE RESTRICT,
  CONSTRAINT fk_events_venue FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NULL,
  movie_id INT NULL,
  venue_space_id INT NOT NULL,
  starts_at DATETIME NOT NULL,
  ends_at DATETIME NOT NULL,
  base_price DECIMAL(10,2) NOT NULL,
  status ENUM('scheduled','cancelled','completed') NOT NULL DEFAULT 'scheduled',
  CONSTRAINT ck_session_time CHECK (ends_at > starts_at),
  CONSTRAINT ck_session_price CHECK (base_price >= 0),
  CONSTRAINT ck_session_target CHECK (
    (event_id IS NOT NULL AND movie_id IS NULL) OR
    (event_id IS NULL AND movie_id IS NOT NULL)
  ),
  INDEX ix_sessions_event_id (event_id),
  INDEX ix_sessions_movie_id (movie_id),
  INDEX ix_sessions_start (starts_at),
  CONSTRAINT fk_sessions_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
  CONSTRAINT fk_sessions_movie FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE RESTRICT,
  CONSTRAINT fk_sessions_space FOREIGN KEY (venue_space_id) REFERENCES venue_spaces(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS seats (
  id INT AUTO_INCREMENT PRIMARY KEY,
  venue_space_id INT NOT NULL,
  row_label VARCHAR(10) NOT NULL,
  seat_number INT NOT NULL,
  seat_type ENUM('standard','premium','recliner') NOT NULL DEFAULT 'standard',
  CONSTRAINT uq_seat_position UNIQUE (venue_space_id, row_label, seat_number),
  CONSTRAINT ck_seat_number CHECK (seat_number > 0),
  INDEX ix_seats_venue_space_id (venue_space_id),
  CONSTRAINT fk_seats_space FOREIGN KEY (venue_space_id) REFERENCES venue_spaces(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  name VARCHAR(100) NOT NULL,
  description VARCHAR(500) NULL,
  price DECIMAL(10,2) NOT NULL,
  capacity INT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT ck_ticket_price CHECK (price >= 0),
  CONSTRAINT ck_ticket_capacity CHECK (capacity > 0),
  CONSTRAINT uq_ticket_type_session_name UNIQUE (session_id, name),
  INDEX ix_ticket_types_session_id (session_id),
  CONSTRAINT fk_ticket_types_session FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_reference VARCHAR(24) NOT NULL UNIQUE,
  user_id INT NOT NULL,
  session_id INT NOT NULL,
  status ENUM('pending','confirmed','cancelled','expired') NOT NULL DEFAULT 'pending',
  total_amount DECIMAL(10,2) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_bookings_user_id (user_id),
  INDEX ix_bookings_session_id (session_id),
  INDEX ix_bookings_status (status),
  CONSTRAINT fk_bookings_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_bookings_session FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS booking_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  ticket_type_id INT NULL,
  seat_id INT NULL,
  quantity INT NOT NULL DEFAULT 1,
  unit_price DECIMAL(10,2) NOT NULL,
  CONSTRAINT ck_booking_quantity CHECK (quantity > 0),
  CONSTRAINT ck_booking_unit_price CHECK (unit_price >= 0),
  CONSTRAINT ck_booking_allocation CHECK (
    (seat_id IS NOT NULL AND ticket_type_id IS NULL AND quantity = 1) OR
    (seat_id IS NULL AND ticket_type_id IS NOT NULL)
  ),
  CONSTRAINT uq_booking_seat_once UNIQUE (booking_id, seat_id),
  INDEX ix_booking_items_booking_id (booking_id),
  INDEX ix_booking_items_ticket_type_id (ticket_type_id),
  INDEX ix_booking_items_seat (seat_id),
  CONSTRAINT fk_booking_items_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
  CONSTRAINT fk_booking_items_ticket_type FOREIGN KEY (ticket_type_id) REFERENCES ticket_types(id) ON DELETE RESTRICT,
  CONSTRAINT fk_booking_items_seat FOREIGN KEY (seat_id) REFERENCES seats(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  provider VARCHAR(60) NOT NULL DEFAULT 'demo',
  provider_reference VARCHAR(150) NULL UNIQUE,
  amount DECIMAL(10,2) NOT NULL,
  status ENUM('initiated','succeeded','failed','refunded') NOT NULL DEFAULT 'initiated',
  paid_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_payments_booking_id (booking_id),
  CONSTRAINT fk_payments_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Verify the final schema:
SHOW TABLES;
