-- 20260709000016_gex_levels_daily.sql
CREATE TABLE gex_levels_daily (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date                DATE NOT NULL,
    underlying          TEXT NOT NULL CHECK (underlying IN ('SPX', 'NDX')),
    call_wall_strike    NUMERIC(10,2),
    put_wall_strike     NUMERIC(10,2),
    gex_flip_strike     NUMERIC(10,2),
    zero_gamma_strike   NUMERIC(10,2),
    max_pain_strike     NUMERIC(10,2),
    total_call_gex      NUMERIC(20,2),
    total_put_gex       NUMERIC(20,2),
    net_gex             NUMERIC(20,2),
    put_call_ratio      NUMERIC(10,4),          -- put OI / call OI
    snapshot_time       TIMESTAMPTZ NOT NULL,   -- time of the source chain snapshot
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (date, underlying, snapshot_time)
);

CREATE INDEX idx_gex_date ON gex_levels_daily (underlying, date DESC);
CREATE INDEX idx_gex_walls ON gex_levels_daily (call_wall_strike, put_wall_strike);
