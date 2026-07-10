-- 20260709000011_key_opens.sql
CREATE TABLE key_opens (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument              TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    session_date            DATE NOT NULL,
    open_type               TEXT NOT NULL CHECK (open_type IN ('18:00', '00:00', '10:00')),
    open_price              NUMERIC(10,2) NOT NULL,
    respected               BOOLEAN,              -- price returned and reversed
    rejected                BOOLEAN,              -- price never returned to open
    time_to_test_minutes    INTEGER,              -- NULL if never tested
    deviation_points        NUMERIC(10,2),        -- max deviation before test
    reversal_magnitude      NUMERIC(10,2),        -- points of reversal after test
    session_type            TEXT CHECK (session_type IN ('London', 'NY_AM', 'NY_PM', 'Overnight', 'Asian')),
    news_day                BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (instrument, session_date, open_type)
);

CREATE INDEX idx_keyopens_instrument_date ON key_opens (instrument, session_date DESC);
CREATE INDEX idx_keyopens_type ON key_opens (instrument, open_type);
CREATE INDEX idx_keyopens_lookup ON key_opens (instrument, open_type, session_date DESC);
CREATE INDEX idx_keyopens_news ON key_opens (instrument, news_day);
