-- 20260709000006_fvg_instances.sql
CREATE TABLE fvg_instances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument      TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    timeframe       TEXT NOT NULL CHECK (timeframe IN ('1m', '5m', '15m', '1H', '4H', 'D')),
    high_bound      NUMERIC(10,2) NOT NULL,
    low_bound       NUMERIC(10,2) NOT NULL,
    gap_size_pts    NUMERIC(10,2) NOT NULL,
    creation_time   TIMESTAMPTZ NOT NULL,
    fill_time       TIMESTAMPTZ,              -- NULL if never fully filled
    fill_pct        NUMERIC(5,2),             -- 0-100, NULL if never touched
    fill_type       TEXT CHECK (fill_type IN ('full', 'partial', 'none', NULL)),
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'filled', 'partial_fill', 'expired')),
    session_type    TEXT CHECK (session_type IN ('London', 'NY_AM', 'NY_PM', 'Overnight', 'Asian')),
    htf_alignment   TEXT CHECK (htf_alignment IN ('aligned', 'counter_trend', 'neutral', NULL)),
    news_day        BOOLEAN DEFAULT FALSE,
    atr_pct         NUMERIC(5,2),             -- gap size as % of ATR at creation
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_fvg_instrument_time ON fvg_instances (instrument, creation_time DESC);
CREATE INDEX idx_fvg_instrument_tf ON fvg_instances (instrument, timeframe);
CREATE INDEX idx_fvg_session ON fvg_instances (instrument, session_type);
CREATE INDEX idx_fvg_status ON fvg_instances (status);
CREATE INDEX idx_fvg_news_day ON fvg_instances (instrument, news_day);
CREATE INDEX idx_fvg_htf_alignment ON fvg_instances (instrument, htf_alignment);

-- Multi-dimensional: common app query pattern
CREATE INDEX idx_fvg_lookup ON fvg_instances (instrument, timeframe, session_type, creation_time DESC);
