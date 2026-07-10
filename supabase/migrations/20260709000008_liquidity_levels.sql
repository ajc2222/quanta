-- 20260709000008_liquidity_levels.sql
CREATE TABLE liquidity_levels (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument              TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    level_type              TEXT NOT NULL CHECK (level_type IN ('BSL', 'SSL')),
    session_type            TEXT CHECK (session_type IN ('London', 'NY_AM', 'NY_PM', 'Overnight', 'Asian')),
    session_date            DATE NOT NULL,
    price                   NUMERIC(10,2) NOT NULL,
    swept                   BOOLEAN NOT NULL DEFAULT FALSE,
    sweep_time              TIMESTAMPTZ,
    post_sweep_direction    TEXT CHECK (post_sweep_direction IN ('bullish', 'bearish', 'neutral', NULL)),
    magnitude               NUMERIC(10,2),     -- points moved after sweep
    double_sweep            BOOLEAN DEFAULT FALSE,  -- both BSL and SSL swept same session
    news_day                BOOLEAN DEFAULT FALSE,
    htf_alignment           TEXT CHECK (htf_alignment IN ('aligned', 'counter_trend', 'neutral', NULL)),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_liq_instrument_date ON liquidity_levels (instrument, session_date DESC);
CREATE INDEX idx_liq_type ON liquidity_levels (instrument, level_type);
CREATE INDEX idx_liq_swept ON liquidity_levels (instrument, swept);
CREATE INDEX idx_liq_session ON liquidity_levels (instrument, session_type);
CREATE INDEX idx_liq_lookup ON liquidity_levels (instrument, level_type, session_type, session_date DESC);
