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
