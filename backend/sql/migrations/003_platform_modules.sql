-- CineBook migration 003: account, organizer, moderation, refunds, reviews,
-- notifications, check-in, audit trail, reports and event seating.
-- Back up cinebook_db before applying. Safe to re-run on MySQL 8.0.29+.

USE cinebook_db;
SET @schema_name = DATABASE();

-- Movie sessions use assigned seats. Events default to general admission until
-- an organizer/admin explicitly creates an assigned-seat session.
SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='sessions' AND COLUMN_NAME='booking_mode') = 0,
  'ALTER TABLE sessions ADD COLUMN booking_mode ENUM(''assigned'',''general_admission'') NOT NULL DEFAULT ''general_admission''',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;
UPDATE sessions SET booking_mode='assigned' WHERE movie_id IS NOT NULL;

-- Events created by an organizer must be reviewed before appearing publicly.
ALTER TABLE events
  MODIFY COLUMN status ENUM('draft','pending_approval','published','cancelled','completed','rejected')
  NOT NULL DEFAULT 'draft';

CREATE TABLE IF NOT EXISTS organizer_applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  organization_name VARCHAR(200) NOT NULL,
  contact_phone VARCHAR(30) NOT NULL,
  website VARCHAR(500) NULL,
  description TEXT NOT NULL,
  status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  reviewed_by INT NULL,
  reviewed_at DATETIME NULL,
  review_note VARCHAR(1000) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_organizer_applications_status (status),
  CONSTRAINT fk_organizer_applications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_organizer_applications_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  used_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_password_reset_tokens_user (user_id),
  INDEX ix_password_reset_tokens_expiry (expires_at),
  CONSTRAINT fk_password_reset_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(180) NOT NULL,
  message VARCHAR(1000) NOT NULL,
  kind VARCHAR(40) NOT NULL DEFAULT 'info',
  link VARCHAR(500) NULL,
  read_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_notifications_user_created (user_id, created_at),
  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS event_reviews (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  user_id INT NOT NULL,
  booking_id INT NOT NULL UNIQUE,
  rating TINYINT NOT NULL,
  comment VARCHAR(2000) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_event_review_user UNIQUE (event_id, user_id),
  CONSTRAINT ck_event_review_rating CHECK (rating BETWEEN 1 AND 5),
  INDEX ix_event_reviews_event (event_id),
  CONSTRAINT fk_event_reviews_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
  CONSTRAINT fk_event_reviews_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_event_reviews_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS refund_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL UNIQUE,
  user_id INT NOT NULL,
  payment_id INT NULL,
  reason VARCHAR(1000) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  status ENUM('requested','approved','rejected','processed') NOT NULL DEFAULT 'requested',
  reviewed_by INT NULL,
  reviewed_at DATETIME NULL,
  resolution_note VARCHAR(1000) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_refund_requests_status (status),
  CONSTRAINT fk_refund_requests_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE RESTRICT,
  CONSTRAINT fk_refund_requests_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_refund_requests_payment FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL,
  CONSTRAINT fk_refund_requests_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  actor_id INT NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(80) NOT NULL,
  entity_id INT NULL,
  details LONGTEXT NULL,
  ip_address VARCHAR(45) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_audit_logs_actor (actor_id),
  INDEX ix_audit_logs_action (action),
  INDEX ix_audit_logs_entity (entity_type, entity_id),
  INDEX ix_audit_logs_created (created_at),
  CONSTRAINT fk_audit_logs_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Ticket QR redemption/check-in is single-use.
SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='booking_tickets' AND COLUMN_NAME='checked_in_at') = 0,
  'ALTER TABLE booking_tickets ADD COLUMN checked_in_at DATETIME NULL',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='booking_tickets' AND COLUMN_NAME='checked_in_by') = 0,
  'ALTER TABLE booking_tickets ADD COLUMN checked_in_by INT NULL, ADD CONSTRAINT fk_booking_tickets_checked_in_by FOREIGN KEY (checked_in_by) REFERENCES users(id) ON DELETE SET NULL',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Reporting views.
CREATE OR REPLACE VIEW vw_cinebook_event_sales AS
SELECT
  e.id AS event_id, e.title AS event_title, e.organizer_id,
  c.name AS city_name, COUNT(DISTINCT b.id) AS confirmed_bookings,
  COALESCE(SUM(CASE WHEN b.status='confirmed' THEN b.total_amount ELSE 0 END),0) AS gross_sales,
  COALESCE(SUM(CASE WHEN rr.status='processed' THEN rr.amount ELSE 0 END),0) AS processed_refunds
FROM events e
JOIN cities c ON c.id=e.city_id
LEFT JOIN sessions s ON s.event_id=e.id
LEFT JOIN bookings b ON b.session_id=s.id
LEFT JOIN refund_requests rr ON rr.booking_id=b.id
GROUP BY e.id,e.title,e.organizer_id,c.name;

CREATE OR REPLACE VIEW vw_cinebook_daily_sales AS
SELECT DATE(b.created_at) AS sales_date, COUNT(*) AS bookings,
       SUM(CASE WHEN b.status='confirmed' THEN b.total_amount ELSE 0 END) AS gross_sales
FROM bookings b
GROUP BY DATE(b.created_at);

-- Scheduled jobs can call this procedure from cron/Task Scheduler. The app also
-- exposes a protected maintenance endpoint; the database is not given a hidden
-- event scheduler dependency.
DROP PROCEDURE IF EXISTS sp_cinebook_cleanup_expired_holds;
DELIMITER $$
CREATE PROCEDURE sp_cinebook_cleanup_expired_holds()
BEGIN
  DELETE FROM show_seat_holds WHERE expires_at <= NOW();
  UPDATE bookings
     SET status='expired'
   WHERE status='pending' AND expires_at IS NOT NULL AND expires_at <= NOW();
END$$
DELIMITER ;

-- Database-level audit records for direct SQL writes as well as API writes.
DROP TRIGGER IF EXISTS trg_cinebook_booking_audit_insert;
DELIMITER $$
CREATE TRIGGER trg_cinebook_booking_audit_insert
AFTER INSERT ON bookings
FOR EACH ROW
BEGIN
  INSERT INTO audit_logs(actor_id,action,entity_type,entity_id,details)
  VALUES (NEW.user_id,'booking.created','booking',NEW.id,
          JSON_OBJECT('booking_reference',NEW.booking_reference,'total_amount',NEW.total_amount));
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_cinebook_payment_audit_update;
DELIMITER $$
CREATE TRIGGER trg_cinebook_payment_audit_update
AFTER UPDATE ON payments
FOR EACH ROW
BEGIN
  IF OLD.status <> NEW.status THEN
    INSERT INTO audit_logs(actor_id,action,entity_type,entity_id,details)
    VALUES (NULL,'payment.status_changed','payment',NEW.id,
            JSON_OBJECT('booking_id',NEW.booking_id,'from',OLD.status,'to',NEW.status));
  END IF;
END$$
DELIMITER ;

SELECT 'CineBook migration 003 applied' AS migration_status;
