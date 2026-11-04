-- CineBook migration 002: venue / show seat inventory / ticket metadata.
-- Run after backing up cinebook_db. This migration is idempotent on MySQL 8.0.29+.
-- Existing cities, venues, events, seats, bookings and demo accounts are preserved.

USE cinebook_db;

SET @schema_name = DATABASE();

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='sessions' AND COLUMN_NAME='tax_percent') = 0,
  'ALTER TABLE sessions ADD COLUMN tax_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='sessions' AND COLUMN_NAME='convenience_fee') = 0,
  'ALTER TABLE sessions ADD COLUMN convenience_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='seats' AND COLUMN_NAME='seat_category') = 0,
  'ALTER TABLE seats ADD COLUMN seat_category VARCHAR(40) NOT NULL DEFAULT ''Standard''',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='bookings' AND COLUMN_NAME='subtotal_amount') = 0,
  'ALTER TABLE bookings ADD COLUMN subtotal_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='bookings' AND COLUMN_NAME='tax_amount') = 0,
  'ALTER TABLE bookings ADD COLUMN tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='bookings' AND COLUMN_NAME='convenience_amount') = 0,
  'ALTER TABLE bookings ADD COLUMN convenience_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='bookings' AND COLUMN_NAME='expires_at') = 0,
  'ALTER TABLE bookings ADD COLUMN expires_at DATETIME NULL, ADD INDEX ix_bookings_expiry (expires_at)',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='bookings' AND COLUMN_NAME='ticket_code') = 0,
  'ALTER TABLE bookings ADD COLUMN ticket_code VARCHAR(64) NULL, ADD UNIQUE INDEX uq_bookings_ticket_code (ticket_code)',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS show_seat_holds (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  seat_id INT NOT NULL,
  user_id INT NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_show_seat_hold UNIQUE (session_id, seat_id),
  INDEX ix_show_seat_holds_expiry (expires_at),
  INDEX ix_show_seat_holds_user (user_id),
  CONSTRAINT fk_show_seat_holds_session FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
  CONSTRAINT fk_show_seat_holds_seat FOREIGN KEY (seat_id) REFERENCES seats(id) ON DELETE CASCADE,
  CONSTRAINT fk_show_seat_holds_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS booking_tickets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL UNIQUE,
  ticket_code VARCHAR(64) NOT NULL UNIQUE,
  issued_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_booking_tickets_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
) ENGINE=InnoDB;

SELECT 'CineBook migration 002 applied' AS migration_status;
