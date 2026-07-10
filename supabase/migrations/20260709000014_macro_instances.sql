-- 20260709000014_macro_instances.sql
CREATE TABLE macro_instances (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                  TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    session_date                DATE NOT NULL,
    macro_type                  TEXT NOT NULL CHECK (macro_type IN (
        'Macro_1', 'Macro_2', 'Lunch', 'NY_PM', 'Close'
    )),
    window_open                 TIMESTAMPTZ NOT NULL,
    window_close                TIMESTAMPTZ NOT NULL,
    open_price                  NUMERIC(10,2) NOT NULL,
    hod                         NUMERIC(10,2) NOT NULL,
    lod                         NUMERIC(10,2) NOT NULL,
    hod_time                    TIMESTAMPTZ NOT NULL,
    lod_time                    TIMESTAMPTZ NOT NULL,
    close_price                 NUMERIC(10,2) NOT NULL,
    direction                   TEXT CHECK (direction IN ('bullish', 'bearish', 'choppy')),
    avg_move_points             NUMERIC(10,2),
    reversal                    BOOLEAN,          -- reversed pre-macro move
    continuation                BOOLEAN,          -- extended pre-macro move
    preceding_po3_phase         TEXT CHECK (preceding_po3_phase IN ('bullish', 'bearish', 'unconfirmed', NULL)),
    hod_of_day_already_made     BOOLEAN,
    lod_of_day_already_made     BOOLEAN,
    news_flag                   BOOLEAN NOT NULL DEFAULT FALSE,
    london_direction            TEXT CHECK (london_direction IN ('bullish', 'bearish', 'neutral', NULL)),
    ny_open_30m_direction       TEXT CHECK (ny_open_30m_direction IN ('bullish', 'bearish', 'neutral', NULL)),
    nearest_pd_array_type       TEXT CHECK (nearest_pd_array_type IN ('FVG', 'OB', 'KEY_OPEN', 'ROUND_NUMBER', NULL)),
    nearest_pd_array_id         UUID,
    nearest_pd_array_distance   NUMERIC(10,2),    -- points to nearest PD array at macro open
    gex_proximity               TEXT CHECK (gex_proximity IN ('at_call_wall', 'at_put_wall', 'near_call_wall', 'near_put_wall', 'neutral', NULL)),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (instrument, session_date, macro_type)
);

CREATE INDEX idx_macro_instrument_date ON macro_instances (instrument, session_date DESC);
CREATE INDEX idx_macro_type ON macro_instances (instrument, macro_type);
CREATE INDEX idx_macro_phase ON macro_instances (preceding_po3_phase);
CREATE INDEX idx_macro_news ON macro_instances (news_flag);
CREATE INDEX idx_macro_lookup ON macro_instances (instrument, macro_type, session_date DESC);
