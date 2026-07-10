"""Supabase Postgres connection pool + batched insert helpers."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime as _datetime
from typing import Any

import psycopg2
import psycopg2.pool
import psycopg2.extras

log = logging.getLogger("pipeline.db")


_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def init_pool(dsn: str, minconn: int = 1, maxconn: int = 5) -> None:
    global _pool
    _pool = psycopg2.pool.ThreadedConnectionPool(minconn, maxconn, dsn)


@contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def upsert_ohlcv_1m(rows: list[dict[str, Any]]) -> int:
    """Upsert 1-min OHLCV bars. Returns inserted/updated row count."""
    if not rows:
        return 0
    sql = """
        INSERT INTO ohlcv_1m (instrument, ts, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (instrument, ts) DO UPDATE
        SET open = EXCLUDED.open,
            high = GREATEST(ohlcv_1m.high, EXCLUDED.high),
            low  = LEAST(ohlcv_1m.low, EXCLUDED.low),
            close = EXCLUDED.close,
            volume = ohlcv_1m.volume + EXCLUDED.volume
    """
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur, sql, rows,
            template="(%(instrument)s, %(ts)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)",
        )
        return cur.rowcount


def upsert_news_events(rows: list[dict[str, Any]]) -> int:
    """Upsert ForexFactory news events."""
    if not rows:
        return 0
    sql = """
        INSERT INTO news_events (event_date, event_time, currency, impact, event_name, actual, forecast, previous)
        VALUES %s
        ON CONFLICT (event_date, event_time, event_name, currency) DO NOTHING
    """
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)
        return cur.rowcount


def insert_options_snapshot(rows: list[dict[str, Any]]) -> int:
    """Insert options chain snapshot rows (call/put per-strike split)."""
    if not rows:
        return 0
    sql = """
        INSERT INTO options_chain_snapshots
            (snapshot_timestamp, underlying, strike, expiry,
             call_oi, put_oi, call_gamma, put_gamma,
             call_delta, put_delta, call_iv, put_iv,
             call_volume, put_volume, spot_price)
        VALUES %s
    """
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)
        return cur.rowcount


def insert_gex_levels(rows: list[dict[str, Any]]) -> int:
    """Insert per-strike GEX levels for a snapshot."""
    if not rows:
        return 0
    sql = """
        INSERT INTO gex_strike_levels
            (snapshot_timestamp, date, underlying, strike, call_gex, put_gex, net_gex)
        VALUES %s
    """
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)
        return cur.rowcount


def upsert_gex_summary(row: dict[str, Any]) -> None:
    """Insert or update the GEX summary for this snapshot."""
    sql = """
        INSERT INTO gex_levels_daily
            (snapshot_timestamp, date, underlying, total_call_gex, total_put_gex,
             net_gex, call_wall_strike, put_wall_strike, gex_flip_strike,
             zero_gamma_strike, max_pain_strike, spot_price)
        VALUES %s
        ON CONFLICT (date, underlying, snapshot_timestamp) DO UPDATE
        SET total_call_gex = EXCLUDED.total_call_gex,
            total_put_gex  = EXCLUDED.total_put_gex,
            net_gex        = EXCLUDED.net_gex,
            call_wall_strike  = EXCLUDED.call_wall_strike,
            put_wall_strike   = EXCLUDED.put_wall_strike,
            gex_flip_strike   = EXCLUDED.gex_flip_strike,
            zero_gamma_strike = EXCLUDED.zero_gamma_strike,
            max_pain_strike   = EXCLUDED.max_pain_strike,
            spot_price        = EXCLUDED.spot_price
    """
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur, sql, [row],
            template="(%(snapshot_timestamp)s, %(date)s, %(underlying)s, %(total_call_gex)s, "
                     "%(total_put_gex)s, %(net_gex)s, %(call_wall_strike)s, %(put_wall_strike)s, "
                     "%(gex_flip_strike)s, %(zero_gamma_strike)s, %(max_pain_strike)s, %(spot_price)s)",
        )


def get_latest_bar_timestamp(instrument: str) -> _datetime | None:
    """Return the latest bar timestamp for *instrument* in ohlcv_1m, or None."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT MAX(ts) FROM ohlcv_1m WHERE instrument = %s", (instrument,))
        row = cur.fetchone()
        return row[0] if row and row[0] else None
