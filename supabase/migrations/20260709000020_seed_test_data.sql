-- 20260709000020_seed_test_data.sql

-- -- Seed sessions (one-time lookup data) --
INSERT INTO sessions (instrument, session_date, session_type, open_time, close_time)
VALUES
    ('ES', '2024-01-02', 'London',   '2024-01-02 03:00:00 ET', '2024-01-02 12:00:00 ET'),
    ('ES', '2024-01-02', 'NY_AM',    '2024-01-02 09:30:00 ET', '2024-01-02 12:00:00 ET'),
    ('ES', '2024-01-02', 'NY_PM',    '2024-01-02 12:00:00 ET', '2024-01-02 17:00:00 ET'),
    ('ES', '2024-01-02', 'Overnight','2024-01-02 18:00:00 ET', '2024-01-03 09:30:00 ET'),
    ('ES', '2024-01-02', 'Asian',    '2024-01-02 19:00:00 ET', '2024-01-03 03:00:00 ET');
