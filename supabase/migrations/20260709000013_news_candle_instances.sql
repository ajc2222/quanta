-- 20260709000013_news_candle_instances.sql
CREATE TABLE news_candle_instances (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument          TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    event_id            UUID NOT NULL REFERENCES news_events(id) ON DELETE CASCADE,
    candle_time         TIMESTAMPTZ NOT NULL,     -- 1-min candle at event release
    candle_open         NUMERIC(10,2) NOT NULL,
    candle_high         NUMERIC(10,2) NOT NULL,
    candle_low          NUMERIC(10,2) NOT NULL,
    candle_close        NUMERIC(10,2) NOT NULL,
    high_taken          BOOLEAN DEFAULT FALSE,    -- swept same session
    low_taken           BOOLEAN DEFAULT FALSE,
    first_side_taken    TEXT CHECK (first_side_taken IN ('high', 'low', NULL)),
    time_to_take_high   INTEGER,                  -- minutes from release to high sweep
    time_to_take_low    INTEGER,                  -- minutes from release to low sweep
    session_type        TEXT CHECK (session_type IN ('London', 'NY_AM', 'NY_PM', 'Overnight', 'Asian')),
    magnitude_after     NUMERIC(10,2),            -- points after first level taken
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (instrument, event_id)
);

CREATE INDEX idx_newscandle_instrument ON news_candle_instances (instrument, candle_time DESC);
CREATE INDEX idx_newscandle_event ON news_candle_instances (event_id);
CREATE INDEX idx_newscandle_taken ON news_candle_instances (high_taken, low_taken);
