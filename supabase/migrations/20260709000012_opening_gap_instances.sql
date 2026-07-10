-- 20260709000012_opening_gap_instances.sql
CREATE TABLE opening_gap_instances (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument          TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    session_date        DATE NOT NULL,            -- date of the new session
    gap_type            TEXT NOT NULL CHECK (gap_type IN ('NDOG', 'NWOG')),
    gap_size_pts        NUMERIC(10,2) NOT NULL,
    gap_direction       TEXT NOT NULL CHECK (gap_direction IN ('bullish', 'bearish')),
    fill_status         TEXT NOT NULL DEFAULT 'unfilled' CHECK (fill_status IN ('filled', 'partial_fill', 'mitigated', 'unfilled')),
    fill_time           TIMESTAMPTZ,
    fill_pct            NUMERIC(5,2),
    fill_session        TEXT CHECK (fill_session IN ('London', 'NY_AM', 'NY_PM', 'Overnight', 'Asian')),
    close_price_prior   NUMERIC(10,2) NOT NULL,   -- prior close
    open_price_gap      NUMERIC(10,2) NOT NULL,   -- gap open
    news_flag           BOOLEAN DEFAULT FALSE,
    htf_alignment       TEXT CHECK (htf_alignment IN ('aligned', 'counter_trend', 'neutral', NULL)),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (instrument, session_date, gap_type)
);

CREATE INDEX idx_gap_instrument_date ON opening_gap_instances (instrument, session_date DESC);
CREATE INDEX idx_gap_type ON opening_gap_instances (gap_type);
CREATE INDEX idx_gap_status ON opening_gap_instances (fill_status);
CREATE INDEX idx_gap_lookup ON opening_gap_instances (instrument, gap_type, session_date DESC);
