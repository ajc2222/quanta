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
        'CREATE TABLE IF NOT EXISTS ohlcv_1m_%I PARTITION OF ohlcv_1m FOR VALUES IN (%L)',
        lower(p_instrument), p_instrument
    );
END;
$$;
