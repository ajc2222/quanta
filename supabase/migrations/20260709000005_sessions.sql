-- 20260709000005_sessions.sql
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument      TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    session_date    DATE NOT NULL,
    session_type    TEXT NOT NULL CHECK (session_type IN ('London', 'NY_AM', 'NY_PM', 'Overnight', 'Asian')),
    open_time       TIMESTAMPTZ NOT NULL,
    close_time      TIMESTAMPTZ NOT NULL,
    session_high    NUMERIC(10,2),
    session_low     NUMERIC(10,2),
    direction       TEXT CHECK (direction IN ('bullish', 'bearish', 'neutral')),
    judas_swing     BOOLEAN DEFAULT FALSE,
    judas_magnitude NUMERIC(10,2),            -- points before reversal
    range_points    NUMERIC(10,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (instrument, session_date, session_type)
);

CREATE INDEX idx_sessions_instrument_date ON sessions (instrument, session_date DESC);
CREATE INDEX idx_sessions_type ON sessions (session_type);
CREATE INDEX idx_sessions_instrument_type_date ON sessions (instrument, session_type, session_date DESC);
