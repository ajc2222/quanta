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
