-- 20260709000004_news_events.sql
CREATE TABLE news_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_date  DATE NOT NULL,
    event_time  TIME NOT NULL,                 -- ET release time
    currency    TEXT NOT NULL,
    impact      TEXT NOT NULL CHECK (impact IN ('High', 'Medium', 'Low')),
    event_name  TEXT NOT NULL,
    actual      TEXT,                          -- actual value (nullable until known)
    forecast    TEXT,
    previous    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_news_events_date ON news_events (event_date);
CREATE INDEX idx_news_events_impact ON news_events (impact);
CREATE INDEX idx_news_events_currency ON news_events (currency);

-- Composite index for the common query: "high-impact events on date X for currency Y"
CREATE INDEX idx_news_events_lookup ON news_events (event_date, impact, currency);
