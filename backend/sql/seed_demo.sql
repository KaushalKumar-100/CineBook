USE cinebook_db;

INSERT IGNORE INTO cities (name, state, country)
VALUES ('Guwahati', 'Assam', 'India'), ('Tezpur', 'Assam', 'India'), ('Delhi', 'Delhi', 'India');

INSERT IGNORE INTO event_categories (name, description)
VALUES ('Concert', 'Live music and concerts'), ('College Fest', 'University and college events'),
       ('Workshop', 'Learning and hands-on sessions'), ('Comedy', 'Stand-up and comedy shows'),
       ('Festival', 'Cultural and community festivals'), ('Cinema Special', 'Special screenings and premieres');
