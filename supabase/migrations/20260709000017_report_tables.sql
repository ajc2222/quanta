-- 20260709000017_report_tables.sql

-- Each report table has:
--   dimension columns identifying the slice
--   stat columns with precomputed values
--   UNIQUE constraint on the dimension set to allow upserts

-- -- report_fvg_stats --
CREATE TABLE report_fvg_stats (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument              TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    timeframe               TEXT NOT NULL,
    session_type            TEXT NOT NULL DEFAULT 'All',
    weekday                 INTEGER NOT NULL DEFAULT -1,   -- 0-6, -1 = all
    news_filter             TEXT NOT NULL DEFAULT 'all' CHECK (news_filter IN ('all', 'news_day', 'non_news_day')),
    htf_bias                TEXT NOT NULL DEFAULT 'all' CHECK (htf_bias IN ('all', 'aligned', 'counter_trend')),
    size_bucket             TEXT NOT NULL DEFAULT 'all' CHECK (size_bucket IN ('all', 'small', 'medium', 'large')),
    lookback_days           TEXT NOT NULL DEFAULT 'all' CHECK (lookback_days IN ('3mo', '6mo', '1yr', 'all')),

    -- Stats
    sample_size             INTEGER NOT NULL DEFAULT 0,
    fill_rate_full_pct      NUMERIC(5,2),
    fill_rate_partial_pct   NUMERIC(5,2),
    avg_fill_time_minutes   NUMERIC(10,2),
    median_fill_time_minutes NUMERIC(10,2),
    avg_fill_pct            NUMERIC(5,2),

    computed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, timeframe, session_type, weekday, news_filter, htf_bias, size_bucket, lookback_days)
);

CREATE INDEX idx_rpt_fvg_lookup ON report_fvg_stats (instrument, timeframe, session_type, lookback_days);


-- -- report_ob_stats --
CREATE TABLE report_ob_stats (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                      TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    timeframe                       TEXT NOT NULL,
    session_type                    TEXT NOT NULL DEFAULT 'All',
    weekday                         INTEGER NOT NULL DEFAULT -1,
    news_filter                     TEXT NOT NULL DEFAULT 'all' CHECK (news_filter IN ('all', 'news_day', 'non_news_day')),
    htf_bias                        TEXT NOT NULL DEFAULT 'all' CHECK (htf_bias IN ('all', 'aligned', 'counter_trend')),
    direction                       TEXT NOT NULL DEFAULT 'all' CHECK (direction IN ('all', 'bullish', 'bearish')),
    lookback_days                   TEXT NOT NULL DEFAULT 'all',

    -- Stats
    sample_size                     INTEGER NOT NULL DEFAULT 0,
    respect_rate_pct                NUMERIC(5,2),
    break_rate_pct                  NUMERIC(5,2),
    avg_mitigation_time_minutes     NUMERIC(10,2),
    avg_reversal_magnitude_points   NUMERIC(10,2),
    breaker_conversion_rate_pct     NUMERIC(5,2),

    computed_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, timeframe, session_type, weekday, news_filter, htf_bias, direction, lookback_days)
);

CREATE INDEX idx_rpt_ob_lookup ON report_ob_stats (instrument, timeframe, session_type, lookback_days);


-- -- report_liquidity_stats --
CREATE TABLE report_liquidity_stats (
    id                                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                          TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    level_type                          TEXT NOT NULL DEFAULT 'all' CHECK (level_type IN ('all', 'BSL', 'SSL')),
    session_type                        TEXT NOT NULL DEFAULT 'All',
    weekday                             INTEGER NOT NULL DEFAULT -1,
    news_filter                         TEXT NOT NULL DEFAULT 'all' CHECK (news_filter IN ('all', 'news_day', 'non_news_day')),
    htf_bias                            TEXT NOT NULL DEFAULT 'all' CHECK (htf_bias IN ('all', 'aligned', 'counter_trend')),
    lookback_days                       TEXT NOT NULL DEFAULT 'all',

    -- Stats
    sample_size                         INTEGER NOT NULL DEFAULT 0,
    sweep_rate_pct                      NUMERIC(5,2),
    reversal_after_sweep_pct            NUMERIC(5,2),
    continuation_after_sweep_pct        NUMERIC(5,2),
    avg_reversal_magnitude_points       NUMERIC(10,2),
    double_sweep_rate_pct               NUMERIC(5,2),

    computed_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, level_type, session_type, weekday, news_filter, htf_bias, lookback_days)
);

CREATE INDEX idx_rpt_liq_lookup ON report_liquidity_stats (instrument, level_type, session_type, lookback_days);


-- -- report_po3_stats --
CREATE TABLE report_po3_stats (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                      TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    window_type                     TEXT NOT NULL,
    weekday                         INTEGER NOT NULL DEFAULT -1,
    phase_filter                    TEXT NOT NULL DEFAULT 'all' CHECK (phase_filter IN ('all', 'bullish', 'bearish', 'unconfirmed')),
    news_filter                     TEXT NOT NULL DEFAULT 'all' CHECK (news_filter IN ('all', 'news_day', 'non_news_day')),
    htf_bias                        TEXT NOT NULL DEFAULT 'all',   -- fractal filter: 'Daily_bullish', 'Daily_bearish', etc.
    lookback_days                   TEXT NOT NULL DEFAULT 'all',

    -- Stats
    sample_size                     INTEGER NOT NULL DEFAULT 0,
    bullish_rate_pct                NUMERIC(5,2),
    bearish_rate_pct                NUMERIC(5,2),
    ambiguous_rate_pct              NUMERIC(5,2),
    avg_range_points                NUMERIC(10,2),
    avg_manip_depth_pct             NUMERIC(5,2),
    hod_before_lod_rate_pct         NUMERIC(5,2),
    lod_before_hod_rate_pct         NUMERIC(5,2),

    -- Distribution data (JSON for flexible frontend rendering)
    hod_time_distribution           JSONB,       -- histogram: {"09:35": 12, "09:40": 8, ...}
    lod_time_distribution           JSONB,
    pd_array_held_hod_breakdown     JSONB,       -- {"FVG": 45.2, "OB": 30.1, "KEY_OPEN": 12.5, "ROUND_NUMBER": 8.2, "None": 4.0}
    pd_array_held_lod_breakdown     JSONB,

    computed_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, window_type, weekday, phase_filter, news_filter, htf_bias, lookback_days)
);

CREATE INDEX idx_rpt_po3_lookup ON report_po3_stats (instrument, window_type, lookback_days);
CREATE INDEX idx_rpt_po3_htf_filter ON report_po3_stats (instrument, window_type, htf_bias, lookback_days);


-- -- report_keyopen_stats --
CREATE TABLE report_keyopen_stats (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                      TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    open_type                       TEXT NOT NULL CHECK (open_type IN ('18:00', '00:00', '10:00')),
    weekday                         INTEGER NOT NULL DEFAULT -1,
    news_filter                     TEXT NOT NULL DEFAULT 'all' CHECK (news_filter IN ('all', 'news_day', 'non_news_day')),
    session_type                    TEXT NOT NULL DEFAULT 'All',
    lookback_days                   TEXT NOT NULL DEFAULT 'all',

    -- Stats
    sample_size                     INTEGER NOT NULL DEFAULT 0,
    respect_rate_pct                NUMERIC(5,2),
    rejection_rate_pct              NUMERIC(5,2),
    avg_deviation_points            NUMERIC(10,2),
    avg_time_to_test_minutes        NUMERIC(10,2),
    avg_reversal_magnitude_points   NUMERIC(10,2),

    computed_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, open_type, weekday, news_filter, session_type, lookback_days)
);

CREATE INDEX idx_rpt_keyopen_lookup ON report_keyopen_stats (instrument, open_type, lookback_days);


-- -- report_opening_gap_stats --
CREATE TABLE report_opening_gap_stats (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                      TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    gap_type                        TEXT NOT NULL CHECK (gap_type IN ('NDOG', 'NWOG', 'all')),
    weekday                         INTEGER NOT NULL DEFAULT -1,
    news_filter                     TEXT NOT NULL DEFAULT 'all' CHECK (news_filter IN ('all', 'news_day', 'non_news_day')),
    gap_size_bucket                 TEXT NOT NULL DEFAULT 'all' CHECK (gap_size_bucket IN ('all', 'small', 'medium', 'large')),
    htf_bias                        TEXT NOT NULL DEFAULT 'all' CHECK (htf_bias IN ('all', 'aligned', 'counter_trend')),
    lookback_days                   TEXT NOT NULL DEFAULT 'all',

    -- Stats
    sample_size                     INTEGER NOT NULL DEFAULT 0,
    full_fill_rate_pct              NUMERIC(5,2),
    partial_fill_rate_pct           NUMERIC(5,2),
    mitigation_rate_pct             NUMERIC(5,2),
    avg_fill_time_minutes           NUMERIC(10,2),
    avg_fill_time_hours             NUMERIC(10,2),

    computed_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, gap_type, weekday, news_filter, gap_size_bucket, htf_bias, lookback_days)
);

CREATE INDEX idx_rpt_gap_lookup ON report_opening_gap_stats (instrument, gap_type, lookback_days);


-- -- report_news_candle_stats --
CREATE TABLE report_news_candle_stats (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                      TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    event_type                      TEXT NOT NULL DEFAULT 'all',    -- CPI / NFP / FOMC / etc.
    impact_level                    TEXT NOT NULL DEFAULT 'all' CHECK (impact_level IN ('all', 'High', 'Medium', 'Low')),
    release_time                    TEXT NOT NULL DEFAULT 'all',    -- '08:30', '10:00', '14:00', 'all'
    weekday                         INTEGER NOT NULL DEFAULT -1,
    session_type                    TEXT NOT NULL DEFAULT 'All',
    lookback_days                   TEXT NOT NULL DEFAULT 'all',

    -- Stats
    sample_size                     INTEGER NOT NULL DEFAULT 0,
    high_taken_rate_pct             NUMERIC(5,2),
    low_taken_rate_pct              NUMERIC(5,2),
    high_taken_first_pct            NUMERIC(5,2),
    low_taken_first_pct             NUMERIC(5,2),
    both_sides_taken_rate_pct       NUMERIC(5,2),
    avg_time_to_take_minutes        NUMERIC(10,2),
    avg_magnitude_after_taken       NUMERIC(10,2),

    computed_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, event_type, impact_level, release_time, weekday, session_type, lookback_days)
);

CREATE INDEX idx_rpt_newscandle_lookup ON report_news_candle_stats (instrument, event_type, impact_level, lookback_days);


-- -- report_macro_stats --
CREATE TABLE report_macro_stats (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                      TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    macro_type                      TEXT NOT NULL,
    weekday                         INTEGER NOT NULL DEFAULT -1,
    news_filter                     TEXT NOT NULL DEFAULT 'all' CHECK (news_filter IN ('all', 'news_day', 'non_news_day')),
    preceding_po3_phase             TEXT NOT NULL DEFAULT 'all' CHECK (preceding_po3_phase IN ('all', 'bullish', 'bearish', 'unconfirmed')),
    london_bias                     TEXT NOT NULL DEFAULT 'all' CHECK (london_bias IN ('all', 'bullish', 'bearish', 'neutral')),
    ny_open_30m_direction           TEXT NOT NULL DEFAULT 'all' CHECK (ny_open_30m_direction IN ('all', 'bullish', 'bearish', 'neutral')),
    gex_proximity                   TEXT NOT NULL DEFAULT 'all',
    lookback_days                   TEXT NOT NULL DEFAULT 'all',

    -- Stats
    sample_size                     INTEGER NOT NULL DEFAULT 0,
    bullish_rate_pct                NUMERIC(5,2),
    bearish_rate_pct                NUMERIC(5,2),
    choppy_rate_pct                 NUMERIC(5,2),
    avg_move_points                 NUMERIC(10,2),
    reversal_rate_pct               NUMERIC(5,2),
    continuation_rate_pct           NUMERIC(5,2),

    -- Distribution
    hod_time_distribution           JSONB,
    lod_time_distribution           JSONB,

    computed_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, macro_type, weekday, news_filter, preceding_po3_phase, london_bias, ny_open_30m_direction, gex_proximity, lookback_days)
);

CREATE INDEX idx_rpt_macro_lookup ON report_macro_stats (instrument, macro_type, lookback_days);
CREATE INDEX idx_rpt_macro_context ON report_macro_stats (instrument, macro_type, preceding_po3_phase, london_bias, lookback_days);


-- -- report_gex_stats --
CREATE TABLE report_gex_stats (
    id                                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument                          TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ')),
    level_type                          TEXT NOT NULL CHECK (level_type IN ('call_wall', 'put_wall', 'gex_flip', 'zero_gamma', 'max_pain')),
    session_type                        TEXT NOT NULL DEFAULT 'All',
    weekday                             INTEGER NOT NULL DEFAULT -1,
    lookback_days                       TEXT NOT NULL DEFAULT 'all',

    -- Stats
    sample_size                         INTEGER NOT NULL DEFAULT 0,
    respect_rate_pct                    NUMERIC(5,2),
    avg_reversal_magnitude_points       NUMERIC(10,2),
    avg_distance_to_level_at_test       NUMERIC(10,2),

    computed_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (instrument, level_type, session_type, weekday, lookback_days)
);

CREATE INDEX idx_rpt_gex_lookup ON report_gex_stats (instrument, level_type, session_type, lookback_days);
