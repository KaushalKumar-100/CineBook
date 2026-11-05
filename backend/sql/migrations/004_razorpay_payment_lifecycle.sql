-- CineBook migration 004: verified Razorpay payments and provider refunds.
-- Back up cinebook_db before applying. Safe to re-run on MySQL 8.0.29+.

USE cinebook_db;
SET @schema_name = DATABASE();

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='payments' AND COLUMN_NAME='provider_payment_id') = 0,
  'ALTER TABLE payments ADD COLUMN provider_payment_id VARCHAR(150) NULL UNIQUE AFTER provider_reference',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=@schema_name AND TABLE_NAME='refund_requests') > 0,
  'ALTER TABLE refund_requests MODIFY status ENUM(''requested'',''approved'',''rejected'',''processing'',''processed'',''failed'') NOT NULL DEFAULT ''requested''',
  'SELECT 1'
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;
