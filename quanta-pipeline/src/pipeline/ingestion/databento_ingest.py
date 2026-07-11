"""Ingest 1-min OHLCV CME futures bars from Databento.

Two modes:
  - **backfill**: pulls all available history (2018-01-01 onward) for
    instruments that have zero rows in ohlcv_1m.
  - **nightly**: pulls only the latest trading day (today or last Friday
    if run on weekend).

Contract rolls are handled by Databento's continuous contract
(stype_in='continuous').  Back-adjusted continuous prices mean the
series is gap-free across roll dates.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd
import pytz
from databento import Historical

from ..config import Config
from ..db import get_latest_bar_timestamp, upsert_ohlcv_1m
from ._retry import http_retry

log = logging.getLogger("pipeline.ingestion.databento")

ET = pytz.timezone("America/New_York")


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------


@http_retry("databento")
def fetch_ohlcv_1m(
    api_key: str,
    instrument: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """Pull 1-min OHLCV bars from Databento as a DataFrame.

    Expected columns after rename: ts_event, open, high, low, close, volume.
    """
    client = Historical(key=api_key)

    # ponytail: using "ohlcv-1m" schema. If Databento's Python SDK
    # exposes this as a definition_id instead, swap to:
    #   client.timesales.get_range(..., resolution="minute")
    # and then resample from trades internally.
    data = client.timesales.get_range(
        dataset="GLBX.MDP3",
        symbols=[instrument],
        schema="ohlcv-1m",
        start=start.strftime("%Y-%m-%dT%H:%M:%S"),
        end=end.strftime("%Y-%m-%dT%H:%M:%S"),
    )

    if data is None or data.empty:
        return pd.DataFrame()

    df = data.to_df()
    # Rename Databento columns to our canonical names
    df = df.rename(columns={
        "ts_event": "ts",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
    })
    df["instrument"] = instrument
    return df[["instrument", "ts", "open", "high", "low", "close", "volume"]]


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_instrument_nightly(cfg: Config, instrument: str) -> int:
    """Pull the latest trading day for *instrument*. Returns rows inserted."""
    today = datetime.now(ET).date()

    # If run before 18:00 ET, pull yesterday; if weekend, pull Friday
    now_et = datetime.now(ET)
    if now_et.hour < 18:
        target_date = today - pd.Timedelta(days=1)
    else:
        target_date = today

    # Adjust to last weekday if weekend
    while target_date.weekday() >= 5:
        target_date -= pd.Timedelta(days=1)

    start = pd.Timestamp(target_date, tz=ET)
    end = start + pd.Timedelta(days=1)

    log.info("Databento nightly: %s %s -> %s", instrument, start.date(), end.date())
    df = fetch_ohlcv_1m(cfg.databento_api_key, instrument, start, end)
    if df.empty:
        log.warning("Databento nightly: no data for %s on %s", instrument, target_date)
        return 0

    inserted = upsert_ohlcv_1m(df.to_dict("records"))
    log.info("Databento nightly: %s inserted %d rows", instrument, inserted)
    return inserted


def run_instrument_backfill(cfg: Config, instrument: str) -> int:
    """Pull all history for an instrument that has no data. Returns rows inserted."""
    latest = get_latest_bar_timestamp(instrument)
    if latest is not None:
        log.info("Databento backfill: %s already has data up to %s, skipping", instrument, latest)
        return 0

    start = pd.Timestamp("2018-01-01", tz=ET)
    end = pd.Timestamp(datetime.now(ET).date(), tz=ET) + pd.Timedelta(days=1)

    log.info("Databento backfill: %s %s -> %s", instrument, start.date(), end.date())

    # Backfill in 6-month chunks to avoid giant single pulls
    total = 0
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + pd.Timedelta(days=180), end)
        df = fetch_ohlcv_1m(cfg.databento_api_key, instrument, chunk_start, chunk_end)
        if not df.empty:
            total += upsert_ohlcv_1m(df.to_dict("records"))
        chunk_start = chunk_end

    log.info("Databento backfill: %s done, %d rows total", instrument, total)
    return total


def run_all(cfg: Config, backfill: bool = False) -> dict[str, int]:
    """Run nightly (or backfill) for all configured instruments.

    Returns dict of {instrument: row_count}.  One instrument failure does
    not stop the others.
    """
    results: dict[str, int] = {}
    for sym in cfg.futures_instruments:
        try:
            if backfill:
                results[sym] = run_instrument_backfill(cfg, sym)
            else:
                results[sym] = run_instrument_nightly(cfg, sym)
        except Exception:
            log.exception("Databento failed for %s", sym)
            results[sym] = -1  # sentinel for failure
    return results
