# Quanta — Database Schema Implementation Plan
**Date:** 2026-07-09
**Version:** v1.0
**Status:** Implementation plan

---

## 1. Overview

This document defines the complete PostgreSQL schema for Quanta on Supabase. The schema is split across ordered migration files, each grouped by concern.

### Key Design Decisions

- **TimescaleDB unavailable on Supabase** — using native `PARTITION BY LIST` for `ohlcv_1m` instead
- **UUID primary keys** for all instance tables; natural composite keys (`instrument, timestamp`) for `ohlcv_1m` only
- **TEXT with CHECK constraints** over custom enums for session/window types — avoids `ALTER TYPE ... ADD VALUE` migration pain
- **TIMESTAMPTZ** for all timestamps (stored UTC, display in ET via app layer)
- **`service_role` writes**, **authenticated users read**, **admin users have targeted write access** (po3_phase_labels)
- **Polymorphic FK references** for PD array associations in `po3_instances` (FVG vs OB vs Key Open vs Round Number)

### Migration Strategy

Each group below is one migration file in `supabase/migrations/`:

```
20260709000001_extensions.sql
20260709000002_admin_users.sql
20260709000003_ohlcv_1m.sql
20260709000004_news_events.sql
20260709000005_sessions.sql
20260709000006_fvg_instances.sql
20260709000007_order_block_instances.sql
20260709000008_liquidity_levels.sql
20260709000009_po3_instances.sql
20260709000010_po3_phase_labels.sql
20260709000011_key_opens.sql
20260709000012_opening_gap_instances.sql
20260709000013_news_candle_instances.sql
20260709000014_macro_instances.sql
20260709000015_options_chain_snapshots.sql
20260709000016_gex_levels_daily.sql
20260709000017_report_tables.sql
20260709000018_indexes.sql
20260709000019_rls_policies.sql
20260709000020_seed_test_data.sql
```

---

## 2. Complete DDL

### 2.1 Extensions

```sql
-- 20260709000001_extensions.sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 2.2 Admin Users

```sql
-- 20260709000002_admin_users.sql
CREATE TABLE admin_users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id    TEXT NOT NULL UNIQUE,          -- Clerk user ID
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin', 'superadmin')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_admin_users_clerk_id ON admin_users (clerk_id);

-- Helper function for RLS policies
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1 FROM admin_users
        WHERE clerk_id = current_setting('request.jwt.claims', true)::json->>'sub'
    );
$$;
```

### 2.3 OHLCV 1-Minute Bars (Partitioned)

```sql
-- 20260709000003_ohlcv_1m.sql

-- Partitioned parent table
CREATE TABLE ohlcv_1m (
    instrument  TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    ts          TIMESTAMPTZ NOT NULL,
    open        NUMERIC(10,2) NOT NULL,
    high        NUMERIC(10,2) NOT NULL,
    low         NUMERIC(10,2) NOT NULL,
    close       NUMERIC(10,2) NOT NULL,
    volume      BIGINT NOT NULL,
    PRIMARY KEY (instrument, ts)
) PARTITION BY LIST (instrument);

-- One partition per instrument
CREATE TABLE ohlcv_1m_es PARTITION OF ohlcv_1m FOR VALUES IN ('ES');
CREATE TABLE ohlcv_1m_nq PARTITION OF ohlcv_1m FOR VALUES IN ('NQ');
CREATE TABLE ohlcv_1m_gc PARTITION OF ohlcv_1m FOR VALUES IN ('GC');
CREATE TABLE ohlcv_1m_cl PARTITION OF ohlcv_1m FOR VALUES IN ('CL');
CREATE TABLE ohlcv_1m_mes PARTITION OF ohlcv_1m FOR VALUES IN ('MES');
CREATE TABLE ohlcv_1m_mnq PARTITION OF ohlcv_1m FOR VALUES IN ('MNQ');

-- Index on ts within each partition for time-range scans
CREATE INDEX idx_ohlcv_1m_es_ts ON ohlcv_1m_es (ts DESC);
CREATE INDEX idx_ohlcv_1m_nq_ts ON ohlcv_1m_nq (ts DESC);
CREATE INDEX idx_ohlcv_1m_gc_ts ON ohlcv_1m_gc (ts DESC);
CREATE INDEX idx_ohlcv_1m_cl_ts ON ohlcv_1m_cl (ts DESC);
CREATE INDEX idx_ohlcv_1m_mes_ts ON ohlcv_1m_mes (ts DESC);
CREATE INDEX idx_ohlcv_1m_mnq_ts ON ohlcv_1m_mnq (ts DESC);

-- Helper: ensure partitions exist before insert (run daily by pipeline)
CREATE OR REPLACE FUNCTION public.ensure_ohlcv_partition(p_instrument TEXT)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS ohlcv_1m_%s PARTITION OF ohlcv_1m FOR VALUES IN (%L)',
        lower(p_instrument), p_instrument
    );
END;
$$;
```

### 2.4 News Events (ForexFactory)

```sql
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
```

### 2.5 Sessions

```sql
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
```

### 2.6 FVG Instances

```sql
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
    fill_pct        NUMERIC(5,2),             -- 0–100, NULL if never touched
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
```

### 2.7 Order Block Instances

```sql
-- 20260709000007_order_block_instances.sql
CREATE TABLE order_block_instances (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument              TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    timeframe               TEXT NOT NULL CHECK (timeframe IN ('1m', '5m', '15m', '1H', '4H', 'D')),
    direction               TEXT NOT NULL CHECK (direction IN ('bullish', 'bearish')),
    origin_candle_time      TIMESTAMPTZ NOT NULL,
    ob_high                 NUMERIC(10,2) NOT NULL,
    ob_low                  NUMERIC(10,2) NOT NULL,
    first_test_time         TIMESTAMPTZ,
    outcome                 TEXT CHECK (outcome IN ('respected', 'broken', 'mitigated', 'breaker_converted', 'untested', NULL)),
    reversal_magnitude      NUMERIC(10,2),     -- points of reversal after test
    session_type            TEXT CHECK (session_type IN ('London', 'NY_AM', 'NY_PM', 'Overnight', 'Asian')),
    htf_alignment           TEXT CHECK (htf_alignment IN ('aligned', 'counter_trend', 'neutral', NULL)),
    news_day                BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ob_instrument_time ON order_block_instances (instrument, origin_candle_time DESC);
CREATE INDEX idx_ob_instrument_tf ON order_block_instances (instrument, timeframe);
CREATE INDEX idx_ob_outcome ON order_block_instances (instrument, outcome);
CREATE INDEX idx_ob_session ON order_block_instances (instrument, session_type);
CREATE INDEX idx_ob_htf_alignment ON order_block_instances (instrument, htf_alignment);
CREATE INDEX idx_ob_lookup ON order_block_instances (instrument, timeframe, session_type, origin_candle_time DESC);
```

### 2.8 Liquidity Levels (BSL/SSL)

```sql
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
```

### 2.9 PO3 Instances

```sql
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
```

### 2.10 PO3 Phase Labels (Admin Overrides)

```sql
-- 20260709000010_po3_phase_labels.sql
CREATE TABLE po3_phase_labels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po3_instance_id UUID NOT NULL REFERENCES po3_instances(id) ON DELETE CASCADE,
    confirmed_phase TEXT NOT NULL CHECK (confirmed_phase IN ('bullish', 'bearish', 'exclude')),
    admin_user_id   UUID NOT NULL REFERENCES admin_users(id),
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (po3_instance_id)
);

CREATE INDEX idx_po3_labels_instance ON po3_phase_labels (po3_instance_id);
```

### 2.11 Key Opens

```sql
-- 20260709000011_key_opens.sql
CREATE TABLE key_opens (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument              TEXT NOT NULL CHECK (instrument IN ('ES', 'NQ', 'GC', 'CL', 'MES', 'MNQ')),
    session_date            DATE NOT NULL,
    open_type               TEXT NOT NULL CHECK (open_type IN ('18:00', '00:00', '10:00')),
    open_price              NUMERIC(10,2) NOT NULL,
    respected               BOOLEAN,              -- price returned and reversed
    rejected                BOOLEAN,              -- price never returned to open
    time_to_test_minutes    INTEGER,              -- NULL if never tested
    deviation_points        NUMERIC(10,2),        -- max deviation before test
    reversal_magnitude      NUMERIC(10,2),        -- points of reversal after test
    session_type            TEXT CHECK (session_type IN ('London', 'NY_AM', 'NY_PM', 'Overnight', 'Asian')),
    news_day                BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (instrument, session_date, open_type)
);

CREATE INDEX idx_keyopens_instrument_date ON key_opens (instrument, session_date DESC);
CREATE INDEX idx_keyopens_type ON key_opens (instrument, open_type);
CREATE INDEX idx_keyopens_lookup ON key_opens (instrument, open_type, session_date DESC);
CREATE INDEX idx_keyopens_news ON key_opens (instrument, news_day);
```

### 2.12 Opening Gap Instances (NDOG / NWOG)

```sql
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
```

### 2.13 News Candle Instances

```sql
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
```

### 2.14 Macro Instances

```sql
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
```

### 2.15 Options Chain Snapshots

```sql
-- 20260709000015_options_chain_snapshots.sql
CREATE TABLE options_chain_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_time   TIMESTAMPTZ NOT NULL,
    underlying      TEXT NOT NULL CHECK (underlying IN ('SPX', 'NDX')),
    strike          NUMERIC(10,2) NOT NULL,
    expiry          DATE NOT NULL,
    call_oi         BIGINT,
    put_oi          BIGINT,
    call_gamma      NUMERIC(20,4),
    put_gamma       NUMERIC(20,4),
    call_delta      NUMERIC(10,4),
    put_delta       NUMERIC(10,4),
    call_iv         NUMERIC(10,4),
    put_iv          NUMERIC(10,4),
    call_volume     BIGINT,
    put_volume      BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_options_snapshot_time ON options_chain_snapshots (underlying, snapshot_time DESC);
CREATE INDEX idx_options_strike ON options_chain_snapshots (underlying, strike);
CREATE INDEX idx_options_expiry ON options_chain_snapshots (expiry);

-- Fast lookup: "latest snapshot for SPX by strike"
CREATE INDEX idx_options_latest ON options_chain_snapshots (underlying, snapshot_time DESC, strike);
```

### 2.16 GEX Levels Daily

```sql
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
```

### 2.17 Report Tables (Aggregated)

```sql
-- 20260709000017_report_tables.sql

-- Each report table has:
--   dimension columns identifying the slice
--   stat columns with precomputed values
--   UNIQUE constraint on the dimension set to allow upserts

-- ── report_fvg_stats ──
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


-- ── report_ob_stats ──
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


-- ── report_liquidity_stats ──
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


-- ── report_po3_stats ──
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


-- ── report_keyopen_stats ──
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


-- ── report_opening_gap_stats ──
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


-- ── report_news_candle_stats ──
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


-- ── report_macro_stats ──
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


-- ── report_gex_stats ──
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
```

---

## 3. Indexes Summary

| Table | Index | Purpose |
|---|---|---|
| `ohlcv_1m_*` | `idx_ohlcv_1m_{instr}_ts` | Time-range scans per instrument |
| `news_events` | `idx_news_events_lookup` | Filter by date + impact + currency |
| `sessions` | `idx_sessions_instrument_type_date` | Multi-dim session filter |
| `fvg_instances` | `idx_fvg_lookup` | Primary access pattern: instrument + TF + session + time |
| `order_block_instances` | `idx_ob_lookup` | Same multi-dim pattern |
| `liquidity_levels` | `idx_liq_lookup` | Level type + session + date |
| `po3_instances` | `idx_po3_instrument_window` | Window + date range |
| `key_opens` | `idx_keyopens_lookup` | Open type + date |
| `opening_gap_instances` | `idx_gap_lookup` | Gap type + date |
| `news_candle_instances` | `idx_newscandle_instrument` | Instrument + time |
| `macro_instances` | `idx_macro_lookup` | Macro type + date |
| `options_chain_snapshots` | `idx_options_latest` | Underlying + time + strike |
| `gex_levels_daily` | `idx_gex_date` | Underlying + date |
| All report tables | `idx_rpt_{type}_lookup` | Instrument + primary dimension + lookback |

Covering index design philosophy: all instance table lookups follow the pattern `WHERE instrument = ? AND {dim1} = ? AND {dim2} = ? ORDER BY time DESC`. The composite indexes mirror this order. Report tables are queried by `(instrument, primary_dimension, lookback)` — single index covers 90% of reads.

---

## 4. Row Level Security

### 4.1 Policy Design

Three access tiers:
1. **Service role (pipeline)** — full read/write on all tables. Bypasses RLS entirely (Supabase service_role key).
2. **Authenticated user** — SELECT on all instance and report tables; no INSERT/UPDATE/DELETE.
3. **Admin user** — same as authenticated, plus INSERT/UPDATE on `po3_phase_labels` and `po3_instances.phase` (for manual overrides).

```sql
-- 20260709000019_rls_policies.sql

-- ── Enable RLS on all tables ──
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE ohlcv_1m ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE fvg_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_block_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE liquidity_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE po3_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE po3_phase_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE key_opens ENABLE ROW LEVEL SECURITY;
ALTER TABLE opening_gap_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_candle_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE macro_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE options_chain_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE gex_levels_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_fvg_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_ob_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_liquidity_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_po3_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_keyopen_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_opening_gap_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_news_candle_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_macro_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_gex_stats ENABLE ROW LEVEL SECURITY;


-- ── Admin users table: only admins can read ──
CREATE POLICY "admin_users_select_self"
    ON admin_users FOR SELECT
    USING (clerk_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "admin_users_select_admin"
    ON admin_users FOR SELECT
    USING (is_admin());


-- ── Read-only: authenticated users can SELECT all instance and report tables ──
-- (One representative policy shown; applied identically to all 22 tables above)
CREATE POLICY "authenticated_select"
    ON fvg_instances FOR SELECT
    TO authenticated
    USING (true);

-- Apply the same to all tables (abbreviated in migration; in code, one CREATE POLICY per table):
-- Tables: ohlcv_1m, news_events, sessions, fvg_instances, order_block_instances,
--   liquidity_levels, po3_instances, po3_phase_labels, key_opens, opening_gap_instances,
--   news_candle_instances, macro_instances, options_chain_snapshots, gex_levels_daily,
--   and all report_*_stats tables


-- ── Admin write access: po3_phase_labels ──
CREATE POLICY "admin_insert_po3_labels"
    ON po3_phase_labels FOR INSERT
    TO authenticated
    WITH CHECK (is_admin());

CREATE POLICY "admin_update_po3_labels"
    ON po3_phase_labels FOR UPDATE
    TO authenticated
    USING (is_admin())
    WITH CHECK (is_admin());


-- ── Admin can UPDATE po3_instances.phase when a label is confirmed ──
CREATE POLICY "admin_update_po3_phase"
    ON po3_instances FOR UPDATE
    TO authenticated
    USING (is_admin())
    WITH CHECK (is_admin() AND (OLD.phase IS DISTINCT FROM NEW.phase));


-- ── Service role: full access (pipeline). Supabase service_role key bypasses RLS.
--    No explicit policy needed — service_role is exempt by default when RLS is enabled.
```

### 4.2 Clerk JWT Integration

The `is_admin()` function references `current_setting('request.jwt.claims')`. For this to work with Clerk:

1. Create a **Clerk JWT Template** named `Supabase` with the following claims mapping:
   ```json
   {
     "aud": "authenticated",
     "role": "authenticated",
     "sub": "{{user.id}}",
     "email": "{{user.primary_email_address}}"
   }
   ```
2. When authenticating from the frontend, use Clerk's `getToken({ template: 'Supabase' })` to obtain the Supabase-compatible JWT.
3. Pass the JWT in the `Authorization: Bearer <token>` header to Supabase.

---

## 5. Rollout / Migration Plan

### Step 1: Initialize Supabase Project
```bash
supabase init
supabase link --project-ref <project-ref>
```

### Step 2: Apply Migrations
```bash
# Apply all migrations in order
for f in supabase/migrations/20260709*.sql; do
  supabase db push --db-url "$SUPABASE_DB_URL" < "$f"
done

# Or use Supabase Studio SQL editor for initial deploy
```

### Step 3: Create Admin User(s)
```sql
-- Initial admin user (run in Supabase SQL editor with service_role)
INSERT INTO admin_users (clerk_id, email, role)
VALUES ('user_2example...', 'admin@quanta.com', 'superadmin');
```

### Step 4: Configure Pipeline Service Role
The Python pipeline connects using the Supabase `service_role` key (found in Project Settings > API). This key bypasses RLS and has full write access.

Environment variable:
```
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIs...
```

### Step 5: Seed Lookup Data
```sql
-- Seed sessions (one-time)
INSERT INTO sessions (instrument, session_date, session_type, open_time, close_time)
VALUES
    ('ES', '2024-01-02', 'London',   '2024-01-02 03:00:00 ET', '2024-01-02 12:00:00 ET'),
    ('ES', '2024-01-02', 'NY_AM',    '2024-01-02 09:30:00 ET', '2024-01-02 12:00:00 ET'),
    ('ES', '2024-01-02', 'NY_PM',    '2024-01-02 12:00:00 ET', '2024-01-02 17:00:00 ET'),
    ('ES', '2024-01-02', 'Overnight','2024-01-02 18:00:00 ET', '2024-01-03 09:30:00 ET'),
    ('ES', '2024-01-02', 'Asian',    '2024-01-02 19:00:00 ET', '2024-01-03 03:00:00 ET');
```

---

## 6. Test Queries for Common Access Patterns

### 6.1 FVG: Fill Rate for ES, 15m, NY AM Session, Last 6 Months

```sql
-- Instance query (pipeline writes this to report table)
SELECT
    instrument,
    timeframe,
    session_type,
    COUNT(*) AS sample_size,
    ROUND(COUNT(*) FILTER (WHERE fill_type = 'full') * 100.0 / NULLIF(COUNT(*), 0), 2) AS fill_rate_full_pct,
    ROUND(COUNT(*) FILTER (WHERE fill_type = 'partial') * 100.0 / NULLIF(COUNT(*), 0), 2) AS fill_rate_partial_pct,
    ROUND(AVG(EXTRACT(EPOCH FROM (fill_time - creation_time)) / 60) FILTER (WHERE fill_time IS NOT NULL), 2) AS avg_fill_time_minutes
FROM fvg_instances
WHERE instrument = 'ES'
  AND timeframe = '15m'
  AND session_type = 'NY_AM'
  AND creation_time >= NOW() - INTERVAL '6 months'
GROUP BY instrument, timeframe, session_type;

-- Report table read (app query)
SELECT * FROM report_fvg_stats
WHERE instrument = 'ES'
  AND timeframe = '15m'
  AND session_type = 'NY_AM'
  AND lookback_days = '6mo'
  AND weekday = -1
  AND news_filter = 'all'
  AND htf_bias = 'all'
  AND size_bucket = 'all';
```

### 6.2 PO3: 30m Open Window Phase Rates with Daily Bullish Filter

```sql
-- Instance query
SELECT
    phase,
    COUNT(*) AS cnt,
    ROUND(AVG(range_points), 2) AS avg_range,
    ROUND(AVG(manip_depth_pct), 2) AS avg_manip_depth
FROM po3_instances
WHERE instrument = 'ES'
  AND window_type = '30m_Open'
  AND session_date >= NOW() - INTERVAL '1 year'
  AND EXISTS (
      SELECT 1 FROM po3_instances daily
      WHERE daily.instrument = po3_instances.instrument
        AND daily.session_date = po3_instances.session_date
        AND daily.window_type = 'Daily'
        AND daily.phase = 'bullish'
  )
GROUP BY phase;

-- Report table read
SELECT * FROM report_po3_stats
WHERE instrument = 'ES'
  AND window_type = '30m_Open'
  AND htf_bias = 'Daily_bullish'
  AND lookback_days = '1yr'
  AND weekday = -1
  AND phase_filter = 'all'
  AND news_filter = 'all';
```

### 6.3 Liquidity Sweeps: BSL Sweep Rate by Session and Weekday

```sql
-- Report read
SELECT session_type, weekday,
       sample_size, sweep_rate_pct, reversal_after_sweep_pct
FROM report_liquidity_stats
WHERE instrument = 'ES'
  AND level_type = 'BSL'
  AND lookback_days = 'all'
  AND news_filter = 'all'
  AND htf_bias = 'all'
ORDER BY weekday, session_type;
```

### 6.4 Key Opens: 10:00 Open Respect Rate by Weekday

```sql
SELECT
    EXTRACT(DOW FROM session_date) AS weekday,
    COUNT(*) AS sample_size,
    ROUND(COUNT(*) FILTER (WHERE respected) * 100.0 / COUNT(*), 2) AS respect_rate_pct,
    ROUND(AVG(deviation_points), 2) AS avg_deviation,
    ROUND(AVG(time_to_test_minutes), 1) AS avg_time_to_test
FROM key_opens
WHERE instrument = 'ES'
  AND open_type = '10:00'
  AND session_date >= NOW() - INTERVAL '1 year'
GROUP BY EXTRACT(DOW FROM session_date)
ORDER BY weekday;
```

### 6.5 Macro with Context: Macro_1 Stats When Preceding PO3 Is Bullish

```sql
-- Report read
SELECT * FROM report_macro_stats
WHERE instrument = 'ES'
  AND macro_type = 'Macro_1'
  AND preceding_po3_phase = 'bullish'
  AND lookback_days = '1yr'
  AND weekday = -1
  AND news_filter = 'all'
  AND london_bias = 'all'
  AND ny_open_30m_direction = 'all'
  AND gex_proximity = 'all';
```

### 6.6 GEX: Latest Levels for ES

```sql
SELECT DISTINCT ON (underlying)
    date, call_wall_strike, put_wall_strike, gex_flip_strike,
    zero_gamma_strike, max_pain_strike, net_gex, put_call_ratio
FROM gex_levels_daily
WHERE underlying = 'SPX'
ORDER BY underlying, date DESC;
```

### 6.7 Options Chain: Current OI Distribution by Strike

```sql
SELECT strike, call_oi, put_oi, call_gamma, put_gamma
FROM options_chain_snapshots
WHERE underlying = 'SPX'
  AND snapshot_time = (
      SELECT MAX(snapshot_time) FROM options_chain_snapshots WHERE underlying = 'SPX'
  )
ORDER BY strike;
```

### 6.8 Session Statistics Over Time Range

```sql
SELECT
    session_type,
    ROUND(AVG(range_points), 2) AS avg_range,
    ROUND(AVG(judas_magnitude), 2) AS avg_judas,
    COUNT(*) FILTER (WHERE judas_swing) * 100.0 / COUNT(*) AS judas_swing_pct
FROM sessions
WHERE instrument = 'ES'
  AND session_date >= NOW() - INTERVAL '6 months'
GROUP BY session_type;
```

---

## 7. Design Notes / Considerations

### ohlcv_1m Partitioning
- Native `PARTITION BY LIST (instrument)` with 6 partitions
- Rows per partition: ~2M/year per instrument (525,600 min * 1 instrument)
- ES alone at 7 years: ~3.7M rows — well within Postgres single-table capability, partitioning is for query isolation (no ES data in NQ scans) and future data lifecycle management
- Partition pruning works automatically when queries filter on `instrument`

### NUMERIC Precision
- Price columns: `NUMERIC(10,2)` — supports values up to 99,999,999.99 (NQ is ~20k, ample room)
- Gamma/OI columns: `NUMERIC(20,4)` / `NUMERIC(20,2)` — options chain values can reach billions
- Percentage columns: `NUMERIC(5,2)` — allows 0.00 to 100.00, two decimal places

### JSONB in Report Tables
- `hod_time_distribution`, `lod_time_distribution`: JSONB arrays of `{time: count}` pairs for histogram rendering
- `pd_array_held_hod_breakdown` etc.: JSONB maps of `{type: percentage}` for donut/bar charts
- These are precomputed by the pipeline and read as-is by the app. JSONB keeps the report schema from exploding with one column per histogram bucket.

### UUID Primary Keys
- All instance and report tables use `gen_random_uuid()` for PKs
- Natural keys like `(instrument, session_date, window_type)` get UNIQUE constraints instead of being the PK
- This avoids composite FK references and keeps join queries simple

### Polymorphic PD Array References
- `po3_instances.pd_array_held_hod_type` + `pd_array_held_hod_id` references an FVG, OB, or Key Open by UUID
- No FK constraint because the referenced table is not fixed
- Pipeline enforces referential integrity at write time

---

## 8. Migration Rollback Plan

Each migration file should have a corresponding rollback. Rollbacks are not automated — run manually via SQL if needed:

```sql
-- Reverse order (last migration first)
DROP TABLE IF EXISTS report_gex_stats;
DROP TABLE IF EXISTS report_macro_stats;
DROP TABLE IF EXISTS report_news_candle_stats;
DROP TABLE IF EXISTS report_opening_gap_stats;
DROP TABLE IF EXISTS report_keyopen_stats;
DROP TABLE IF EXISTS report_po3_stats;
DROP TABLE IF EXISTS report_liquidity_stats;
DROP TABLE IF EXISTS report_ob_stats;
DROP TABLE IF EXISTS report_fvg_stats;
DROP TABLE IF EXISTS gex_levels_daily;
DROP TABLE IF EXISTS options_chain_snapshots;
DROP TABLE IF EXISTS macro_instances;
DROP TABLE IF EXISTS news_candle_instances;
DROP TABLE IF EXISTS opening_gap_instances;
DROP TABLE IF EXISTS key_opens;
DROP TABLE IF EXISTS po3_phase_labels;
DROP TABLE IF EXISTS po3_instances;
DROP TABLE IF EXISTS liquidity_levels;
DROP TABLE IF EXISTS order_block_instances;
DROP TABLE IF EXISTS fvg_instances;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS news_events;
DROP TABLE IF EXISTS ohlcv_1m CASCADE;
DROP TABLE IF EXISTS admin_users;
DROP FUNCTION IF EXISTS public.is_admin;
DROP FUNCTION IF EXISTS public.ensure_ohlcv_partition;
```
