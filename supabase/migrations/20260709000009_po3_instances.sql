-- 20260709000009_po3_instances.sql
CREATE TABLE po3_instances (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                  TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    window_type                 TEXT NOT NULL CHECK (window_type IN (
        'Daily', '4H_Morning', '4H_Midday', '30m_Open', '30m_Late', 'NY_Session', '15m_Custom'
    )),
    session_date                DATE NOT NULL,
    window_open                 TIMESTAMPTZ NOT NULL,
    window_close                TIMESTAMPTZ NOT NULL,
    open_price                  NUMERIC(10,2) NOT NULL,
    hod                         NUMERIC(10,2) NOT NULL,
    lod                         NUMERIC(10,2) NOT NULL,
    hod_time                    TIMESTAMPTZ NOT NULL,
    lod_time                    TIMESTAMPTZ NOT NULL,
    close_price                 NUMERIC(10,2) NOT NULL,
    range_points                NUMERIC(10,2) NOT NULL,
    phase                       TEXT NOT NULL CHECK (phase IN ('bullish', 'bearish', 'unconfirmed')),
    manip_depth_pct             NUMERIC(5,2),     -- % of range used for manipulation
    hod_before_lod              BOOLEAN,          -- TRUE = high came first
    news_flag                   BOOLEAN NOT NULL DEFAULT FALSE,
    pd_array_held_hod_type      TEXT CHECK (pd_array_held_hod_type IN ('FVG', 'OB', 'KEY_OPEN', 'ROUND_NUMBER', NULL)),
    pd_array_held_hod_id        UUID,
    pd_array_held_hod_label     TEXT,             -- human-readable: "1H FVG at 4950.25"
    pd_array_held_lod_type      TEXT CHECK (pd_array_held_lod_type IN ('FVG', 'OB', 'KEY_OPEN', 'ROUND_NUMBER', NULL)),
    pd_array_held_lod_id        UUID,
    pd_array_held_lod_label     TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (instrument, window_type, session_date)
);

-- Multi-dimensional lookup: instrument + window + date range
CREATE INDEX idx_po3_instrument_window ON po3_instances (instrument, window_type, session_date DESC);
CREATE INDEX idx_po3_phase ON po3_instances (instrument, phase);
CREATE INDEX idx_po3_news ON po3_instances (instrument, news_flag);
CREATE INDEX idx_po3_session_date ON po3_instances (session_date DESC);
