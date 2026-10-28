-- Idempotent development seed data for CineBook.
-- Run after schema creation. All records here are fictional coursework examples.
USE cinebook_db;

INSERT IGNORE INTO cities (name, state, country)
VALUES ('Guwahati', 'Assam', 'India'),
       ('Tezpur', 'Assam', 'India'),
       ('Delhi', 'Delhi', 'India');

INSERT IGNORE INTO event_categories (name, description)
VALUES ('Concert', 'Live music and concerts'),
       ('College Fest', 'University and college events'),
       ('Workshop', 'Learning and hands-on sessions'),
       ('Comedy', 'Stand-up and comedy shows'),
       ('Festival', 'Cultural and community festivals'),
       ('Exhibition', 'Art, culture, and trade exhibitions'),
       ('Cinema Special', 'Special screenings and premieres');

INSERT INTO venues (city_id, name, venue_type, address)
SELECT c.id, 'CineBook Demo Cinema', 'cinema', 'Demo Road, Guwahati, Assam'
FROM cities c
WHERE c.name = 'Guwahati' AND c.state = 'Assam'
  AND NOT EXISTS (
    SELECT 1 FROM venues v
    WHERE v.city_id = c.id AND v.name = 'CineBook Demo Cinema'
      AND v.address = 'Demo Road, Guwahati, Assam'
  );

INSERT INTO venue_spaces (venue_id, name, space_type, capacity)
SELECT v.id, 'Screen 1', 'screen', 40
FROM venues v
WHERE v.name = 'CineBook Demo Cinema'
  AND NOT EXISTS (
    SELECT 1 FROM venue_spaces s WHERE s.venue_id = v.id AND s.name = 'Screen 1'
  );

INSERT INTO movies (title, synopsis, language, duration_minutes, release_date, certificate, poster_url, is_active)
SELECT 'CineBook Sample Movie',
       'A fictional sample movie used to demonstrate show scheduling and seat bookings.',
       'Hindi', 120, NULL, 'U/A',
       'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba', TRUE
WHERE NOT EXISTS (
  SELECT 1 FROM movies WHERE title = 'CineBook Sample Movie'
);

-- Create a compact 4 x 10 numbered seat layout once.
INSERT IGNORE INTO seats (venue_space_id, row_label, seat_number, seat_type)
SELECT s.id, rows_data.row_label, numbers.seat_number, 'standard'
FROM venue_spaces s
JOIN venues v ON v.id = s.venue_id
JOIN cities c ON c.id = v.city_id
CROSS JOIN (
  SELECT 'A' AS row_label UNION ALL SELECT 'B' UNION ALL
  SELECT 'C' UNION ALL SELECT 'D'
) AS rows_data
CROSS JOIN (
  SELECT 1 AS seat_number UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL
  SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL
  SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
) AS numbers
WHERE v.name = 'CineBook Demo Cinema' AND s.name = 'Screen 1'
  AND c.name = 'Guwahati' AND c.state = 'Assam';

-- Schedule one future sample show if no future sample show exists for this screen.
INSERT INTO sessions (event_id, movie_id, venue_space_id, starts_at, ends_at, base_price, status)
SELECT NULL, m.id, s.id,
       DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 7 DAY),
       DATE_ADD(DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 7 DAY), INTERVAL m.duration_minutes MINUTE),
       250.00, 'scheduled'
FROM movies m
JOIN venue_spaces s ON s.name = 'Screen 1'
JOIN venues v ON v.id = s.venue_id AND v.name = 'CineBook Demo Cinema'
JOIN cities c ON c.id = v.city_id AND c.name = 'Guwahati' AND c.state = 'Assam'
WHERE m.title = 'CineBook Sample Movie'
  AND NOT EXISTS (
    SELECT 1 FROM sessions x
    WHERE x.movie_id = m.id AND x.venue_space_id = s.id
      AND x.starts_at > CURRENT_TIMESTAMP
  );

-- Event organizers should first register through POST /api/v1/auth/register,
-- then an admin may promote an account to organizer. Add events with the API.
SELECT 'Seed data ready' AS status;
