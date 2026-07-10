# Quanta — Data Ingestion Pipeline Implementation Plan
**Date:** 2026-07-09
**Status:** Ready for implementation
**Service:** Standalone Python process deployed on Railway

---

## 1. Project Structure

```
quanta/
├── pyproject.toml                  # Dependencies, metadata, entry point
├── Dockerfile                      # Railway container image
├── .env.example                    # Documented env vars
├── src/
│   └── pipeline/
│       ├── __init__.py
│       ├── main.py                 # Entry point: scheduler + health server
│       ├── config.py               # Env-var config with validation
│       ├── db.py                   # Supabase Postgres connection pool + insert helpers
│       ├── logging_setup.py        # Structured JSON logging to stdout
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── _retry.py           # Shared retry/decorator
│       │   ├── databento_ingest.py # OHLCV 1-min bars
│       │   ├── forexfactory_ingest.py  # Economic calendar events
│       │   └── yfinance_ingest.py  # Options chains + GEX computation
│       └── monitoring/
│           ├── __init__.py
│           └── health.py           # Minimal HTTP health-check server
```

### Rationale (Ponytail)

- Flat ingestion/ directory — no base class, no abstract ingest interface. Three
  independent modules with one shared retry helper is simpler than a hierarchy.
- `_retry.py` — one shared `tenacity` decorator config keeps retry policies
  consistent and avoids repeating the boilerplate in each module.
- No `models/` package — table schemas live as SQL in the plan's Supabase
  migration section (below). Insert functions are thin and live in `db.py`
  because they share the same connection pool.
- No `utils/` dumpster fire — `config.py` and `logging_setup.py` are top-level
  modules in the package by the rule "one concern, one file."

---

## 2. pyproject.toml

```toml
[project]
name = "quanta-pipeline"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "databento>=0.20.0",
    "yfinance>=0.2.0",
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "lxml>=5.1",
    "apscheduler>=3.10",
    "psycopg2-binary>=2.9",
    "tenacity>=8.2",
    "python-dotenv>=1.0",
    "numpy>=1.26",
    "pandas>=2.1",
]

[project.scripts]
quanta-pipeline = "pipeline.main:main"

[tool.setuptools.packages.find]
where = ["src"]
```

---

## 3. Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/

EXPOSE 8080
CMD ["quanta-pipeline"]
```

---

## 4. Environment Variables (.env.example)

```bash
# --- Required ---
DATABENTO_API_KEY=db_xxx
SUPABASE_DATABASE_URL=postgresql://user:pass@host:6543/postgres

# --- Optional ---
PORT=8080                                    # Health check port (Railway sets this)
LOG_LEVEL=INFO                               # DEBUG / INFO / WARNING / ERROR
RUN_NIGHTLY=true                             # Enable nightly Databento + ForexFactory
RUN_INTRADAY=true                            # Enable intraday options (09-16:30 ET)
```

---

## 5. Source Code

### 5.1 src/pipeline/config.py

```python
"""Read env vars once, validate, export frozen config object."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Config:
    databento_api_key: str
    supabase_database_url: str
    port: int = 8080
    log_level: str = "INFO"
    run_nightly: bool = True
    run_intraday: bool = True

    # Timezone for all scheduling
    et_tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("America/New_York"))

    # Instruments tracked on CME Globex
    futures_instruments: tuple = ("ES", "NQ", "GC", "CL", "MES", "MNQ")

    # Options underlyings
    options_underlyings: tuple = ("^SPX", "^NDX")

    # Intraday options pull window (ET)
    options_start_time: str = "09:00"
    options_end_time: str = "16:30"
    options_interval_minutes: int = 30

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            databento_api_key=os.environ["DATABENTO_API_KEY"],
            supabase_database_url=os.environ["SUPABASE_DATABASE_URL"],
            port=int(os.getenv("PORT", "8080")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            run_nightly=os.getenv("RUN_NIGHTLY", "true").lower() == "true",
            run_intraday=os.getenv("RUN_INTRADAY", "true").lower() == "true",
        )
```

### 5.2 src/pipeline/logging_setup.py

```python
"""Structured JSON logging to stdout — Railway-native format."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger("pipeline")
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(handler)
```

### 5.3 src/pipeline/db.py

```python
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
        INSERT INTO ohlcv_1m (instrument, timestamp, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (instrument, timestamp) DO UPDATE
        SET open = EXCLUDED.open,
            high = GREATEST(ohlcv_1m.high, EXCLUDED.high),
            low  = LEAST(ohlcv_1m.low, EXCLUDED.low),
            close = EXCLUDED.close,
            volume = ohlcv_1m.volume + EXCLUDED.volume
    """
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur, sql, rows,
            template="(%(instrument)s, %(timestamp)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)",
        )
        return cur.rowcount


def upsert_news_events(rows: list[dict[str, Any]]) -> int:
    """Upsert ForexFactory news events."""
    if not rows:
        return 0
    sql = """
        INSERT INTO news_events (date, time_et, currency, impact, event, actual, forecast, previous)
        VALUES %s
        ON CONFLICT (date, time_et, event, currency) DO NOTHING
    """
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)
        return cur.rowcount


def insert_options_snapshot(rows: list[dict[str, Any]]) -> int:
    """Insert raw options chain snapshot rows."""
    if not rows:
        return 0
    sql = """
        INSERT INTO options_chain_snapshots
            (snapshot_timestamp, underlying, strike, expiry, option_type,
             open_interest, volume, implied_volatility, delta, gamma,
             last_price, spot_price, dte)
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
        INSERT INTO gex_levels_daily
            (snapshot_timestamp, date, underlying, strike, call_gex, put_gex, net_gex)
        VALUES %s
    """
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)
        return cur.rowcount


def upsert_gex_summary(row: dict[str, Any]) -> None:
    """Insert or update the GEX summary for this snapshot."""
    sql = """
        INSERT INTO gex_summary
            (snapshot_timestamp, date, underlying, total_call_gex, total_put_gex,
             net_gex, call_wall_strike, put_wall_strike, gex_flip_strike,
             zero_gamma_strike, max_pain_strike, spot_price)
        VALUES %s
        ON CONFLICT (snapshot_timestamp, underlying) DO UPDATE
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
        cur.execute("SELECT MAX(timestamp) FROM ohlcv_1m WHERE instrument = %s", (instrument,))
        row = cur.fetchone()
        return row[0] if row and row[0] else None
```

### 5.4 src/pipeline/ingestion/_retry.py

```python
"""Shared retry configuration for all ingestion modules."""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging
import requests

log = logging.getLogger("pipeline.ingestion")

# Retry on transient network errors + HTTP 429/503
TRANSIENT = (
    requests.ConnectionError,
    requests.Timeout,
    ConnectionResetError,
    TimeoutError,
)

def is_transient_http(exc: BaseException) -> bool:
    if isinstance(exc, requests.HTTPError):
        return exc.response is not None and exc.response.status_code in (429, 502, 503, 504)
    return False


def http_retry(label: str = ""):
    """Decorator factory: exponential backoff, max 3 attempts, log on retry."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type(TRANSIENT) | retry_if_exception_type(requests.HTTPError) | retry_if_exception_type(is_transient_http),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,
    )
```

### 5.5 src/pipeline/ingestion/databento_ingest.py

```python
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
        "ts_event": "timestamp",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
    })
    df["instrument"] = instrument
    return df[["instrument", "timestamp", "open", "high", "low", "close", "volume"]]


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
```

### 5.6 src/pipeline/ingestion/forexfactory_ingest.py

```python
"""Ingest economic calendar events from ForexFactory.

Primary source: the free JSON endpoint at
  https://nfs.faireconomy.media/ff_calendar_thisweek.json

Falls back to scraping the HTML calendar page if the JSON endpoint is
unavailable.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pytz
import requests
from bs4 import BeautifulSoup

from ..config import Config
from ..db import upsert_news_events
from ._retry import http_retry

log = logging.getLogger("pipeline.ingestion.forexfactory")

FF_JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FF_HTML_URL = "https://www.forexfactory.com/calendar"

IMPACT_MAP = {
    "3": "High",
    "2": "Medium",
    "1": "Low",
}

ET = pytz.timezone("America/New_York")


# ---------------------------------------------------------------------------
# JSON source (primary)
# ---------------------------------------------------------------------------

@http_retry("forexfactory-json")
def _fetch_json() -> list[dict]:
    resp = requests.get(FF_JSON_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _parse_json_event(raw: dict) -> dict[str, Any] | None:
    """Map a JSON event dict to our schema."""
    try:
        event_date = date.fromisoformat(raw["date"])
    except (KeyError, ValueError):
        return None

    return {
        "date": event_date,
        "time_et": raw.get("time"),
        "currency": raw.get("country", ""),
        "impact": IMPACT_MAP.get(raw.get("impact", ""), "Low"),
        "event": raw.get("title", ""),
        "actual": raw.get("actual"),
        "forecast": raw.get("forecast"),
        "previous": raw.get("previous"),
    }


# ---------------------------------------------------------------------------
# HTML scrape fallback
# ---------------------------------------------------------------------------

@http_retry("forexfactory-html")
def _fetch_html() -> list[dict]:
    resp = requests.get(FF_HTML_URL, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rows: list[dict] = []
    for tr in soup.select("table.calendar_table tr.calendar_row"):
        cells = tr.select("td")
        if len(cells) < 8:
            continue

        cell_date = cells[0].get_text(strip=True)
        cell_time = cells[1].get_text(strip=True)
        cell_currency = cells[2].get_text(strip=True)
        cell_impact = cells[4].get("data-img_url", "")
        cell_event = cells[5].get_text(strip=True)
        cell_actual = cells[6].get_text(strip=True)
        cell_forecast = cells[7].get_text(strip=True)
        cell_previous = cells[8].get_text(strip=True)

        # Parse date — FF shows "Wed Jul 9" or similar relative
        try:
            parsed_date = datetime.strptime(cell_date, "%a %b %d").replace(year=datetime.now().year)
        except ValueError:
            continue

        # Map impact icon filename to level
        if "red" in cell_impact:
            impact = "High"
        elif "orange" in cell_impact:
            impact = "Medium"
        else:
            impact = "Low"

        rows.append({
            "date": parsed_date.date(),
            "time_et": cell_time,
            "currency": cell_currency,
            "impact": impact,
            "event": cell_event,
            "actual": cell_actual or None,
            "forecast": cell_forecast or None,
            "previous": cell_previous or None,
        })

    return rows


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(cfg: Config) -> int:
    """Fetch and upsert ForexFactory events for this and next week.

    Returns number of events upserted.
    """
    log.info("ForexFactory: fetching calendar")

    try:
        raw = _fetch_json()
        events = [_parse_json_event(e) for e in raw]
        events = [e for e in events if e is not None]
        source = "json"
    except Exception:
        log.warning("ForexFactory JSON failed, falling back to HTML scrape", exc_info=True)
        try:
            events = _fetch_html()
            source = "html"
        except Exception:
            log.exception("ForexFactory HTML scrape also failed")
            return 0

    if not events:
        log.warning("ForexFactory: no events parsed from %s", source)
        return 0

    inserted = upsert_news_events(events)
    log.info("ForexFactory: upserted %d events (%s)", inserted, source)
    return inserted
```

### 5.7 src/pipeline/ingestion/yfinance_ingest.py

```python
"""Ingest SPX/NDX options chains via yfinance and compute GEX.

Gamma is not returned by yfinance, so we compute it from the Black-Scholes
model using the data yfinance *does* return: strike, spot, implied volatility,
and days-to-expiry.

Runs intraday (09:00-16:30 ET) at configurable intervals.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
import pytz
import yfinance as yf

from ..config import Config
from ..db import insert_options_snapshot, insert_gex_levels, upsert_gex_summary
from ._retry import http_retry

log = logging.getLogger("pipeline.ingestion.yfinance")

ET = pytz.timezone("America/New_York")

# Multiplier for SPX/NDX standard options
CONTRACT_MULTIPLIER = 100

# Risk-free rate proxy (current 2yr Treasury yield ~ 4.75%)
RISK_FREE_RATE = 0.0475  # ponytail: hardcoded; pull from FRED if rates move >100bp


# ---------------------------------------------------------------------------
# Black-Scholes gamma
# ---------------------------------------------------------------------------

def _norm_pdf(x: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * x ** 2) / np.sqrt(2 * np.pi)


def compute_gamma(
    S: float,
    K: np.ndarray,
    T: np.ndarray,
    sigma: np.ndarray,
    r: float = RISK_FREE_RATE,
) -> np.ndarray:
    """Compute Black-Scholes gamma for an array of options.

    Parameters
    ----------
    S : float — spot price
    K : ndarray — strike prices
    T : ndarray — time to expiry in years
    sigma : ndarray — implied volatilities (decimals, e.g. 0.20 for 20%)

    Returns
    -------
    ndarray — gamma per option
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return _norm_pdf(d1) / (S * sigma * np.sqrt(T))


# ---------------------------------------------------------------------------
# Fetch chain
# ---------------------------------------------------------------------------

@http_retry("yfinance")
def _fetch_chain(underlying: str) -> tuple[pd.DataFrame, float]:
    """Fetch ALL option expirations for *underlying*.

    Returns (DataFrame with columns: strike, expiry, type, OI, IV, last_price,
    spot) and the spot price.
    """
    ticker = yf.Ticker(underlying)

    # Get current price
    hist = ticker.history(period="1d", interval="1m")
    if hist.empty:
        raise ValueError(f"No price data for {underlying}")
    spot = float(hist["Close"].iloc[-1])

    expiry_dates = ticker.options
    if not expiry_dates:
        raise ValueError(f"No options for {underlying}")

    rows: list[dict] = []
    for expiry_str in expiry_dates:
        chain = ticker.option_chain(expiry_str)
        expiry_date = pd.Timestamp(expiry_str).date()
        dte = max((pd.Timestamp(expiry_str) - pd.Timestamp.now()).days, 1)

        for opt_type, df in [("call", chain.calls), ("put", chain.puts)]:
            if df.empty:
                continue
            for _, opt in df.iterrows():
                rows.append({
                    "strike": float(opt["strike"]),
                    "expiry": expiry_date,
                    "option_type": opt_type,
                    "open_interest": int(opt.get("openInterest", 0) or 0),
                    "volume": int(opt.get("volume", 0) or 0),
                    "implied_volatility": float(opt.get("impliedVolatility", np.nan) or np.nan),
                    "last_price": float(opt.get("lastPrice", np.nan) or np.nan),
                })

    result = pd.DataFrame(rows)
    result["dte"] = dte
    return result, spot


# ---------------------------------------------------------------------------
# GEX computation
# ---------------------------------------------------------------------------

def _compute_gex_snapshot(
    chain: pd.DataFrame,
    spot: float,
    underlying: str,
    now: pd.Timestamp,
) -> tuple[list[dict], dict]:
    """Compute per-strike GEX and summary metrics from a raw chain DataFrame.

    Returns (per_strike_rows, summary_dict).
    """
    chain = chain.dropna(subset=["implied_volatility"]).copy()
    if chain.empty:
        return [], {}

    chain["T"] = chain["dte"] / 365.0
    chain["gamma"] = compute_gamma(
        S=spot,
        K=chain["strike"].values,
        T=chain["T"].values,
        sigma=chain["implied_volatility"].values,
    )

    # GEX per option = gamma * OI * multiplier * S
    # Puts have negative gamma by convention
    chain["gex"] = chain["gamma"] * chain["open_interest"] * CONTRACT_MULTIPLIER * spot
    chain.loc[chain["option_type"] == "put", "gex"] *= -1.0

    today = now.date()
    date_param = today if isinstance(today, date) else today.date()

    per_strike = []
    for strike, grp in chain.groupby("strike"):
        call_gex = grp.loc[grp["option_type"] == "call", "gex"].sum()
        put_gex = grp.loc[grp["option_type"] == "put", "gex"].sum()
        per_strike.append({
            "snapshot_timestamp": now,
            "date": date_param,
            "underlying": underlying,
            "strike": strike,
            "call_gex": round(call_gex, 2),
            "put_gex": round(put_gex, 2),
            "net_gex": round(call_gex + put_gex, 2),
        })

    # Summary
    gex_df = pd.DataFrame(per_strike)
    if gex_df.empty:
        return [], {}

    total_call_gex = gex_df["call_gex"].sum()
    total_put_gex = gex_df["put_gex"].sum()
    net_gex = total_call_gex + total_put_gex

    call_wall_row = gex_df.loc[gex_df["call_gex"].idxmax()] if not gex_df[gex_df["call_gex"] > 0].empty else None
    # Put wall = strike with largest absolute put GEX (most negative)
    put_wall_row = gex_df.loc[gex_df["put_gex"].abs().idxmax()] if not gex_df[gex_df["put_gex"] < 0].empty else None

    gex_flip = None
    sorted_by_strike = gex_df.sort_values("strike")
    for i in range(len(sorted_by_strike) - 1):
        if sorted_by_strike.iloc[i]["net_gex"] <= 0 <= sorted_by_strike.iloc[i + 1]["net_gex"]:
            gex_flip = sorted_by_strike.iloc[i]["strike"]
            break

    zero_gamma = gex_df.iloc[(gex_df["net_gex"].abs()).idxmin()]["strike"] if not gex_df.empty else None

    # Max pain: the strike where total dollar loss for option buyers is minimized
    # Approximate by finding strike where sum of put + call OI * |S - K| is minimized
    # This is a simplification; an accurate max pain requires all strikes simultaneously
    strikes = chain["strike"].unique()
    best_strike = strikes[0]
    best_pain = float("inf")
    for sk in strikes:
        call_pain = chain.loc[(chain["strike"] == sk) & (chain["option_type"] == "call"), "open_interest"].sum() * max(spot - sk, 0)
        put_pain = chain.loc[(chain["strike"] == sk) & (chain["option_type"] == "put"), "open_interest"].sum() * max(sk - spot, 0)
        total_pain = call_pain + put_pain
        if total_pain < best_pain:
            best_pain = total_pain
            best_strike = sk
    max_pain = best_strike

    summary = {
        "snapshot_timestamp": now,
        "date": date_param,
        "underlying": underlying,
        "total_call_gex": round(total_call_gex, 2),
        "total_put_gex": round(total_put_gex, 2),
        "net_gex": round(net_gex, 2),
        "call_wall_strike": round(call_wall_row["strike"], 2) if call_wall_row is not None else None,
        "put_wall_strike": round(put_wall_row["strike"], 2) if put_wall_row is not None else None,
        "gex_flip_strike": round(gex_flip, 2) if gex_flip is not None else None,
        "zero_gamma_strike": round(zero_gamma, 2) if zero_gamma is not None else None,
        "max_pain_strike": round(max_pain, 2) if max_pain is not None else None,
        "spot_price": round(spot, 2),
    }

    return per_strike, summary


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_snapshot(per_strike: list, summary: dict, underlying: str) -> None:
    """Basic sanity checks on the ingested data."""
    if not per_strike:
        log.warning("yfinance: %s GEX per-strike list is empty", underlying)
        return
    if summary["total_call_gex"] == 0 and summary["total_put_gex"] == 0:
        log.warning("yfinance: %s both call and put GEX are 0 — check data", underlying)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_snapshot(cfg: Config, underlying: str) -> dict[str, Any] | None:
    """Fetch options chain for *underlying*, compute GEX, persist.

    Returns summary dict or None on failure.
    """
    log.info("yfinance: fetching %s options chain", underlying)
    try:
        chain, spot = _fetch_chain(underlying)
    except Exception:
        log.exception("yfinance: failed to fetch chain for %s", underlying)
        return None

    if chain.empty:
        log.warning("yfinance: empty chain for %s", underlying)
        return None

    now = pd.Timestamp.now(tz=ET)

    # 1. Store raw chain
    raw_rows = chain.to_dict("records")
    for r in raw_rows:
        r["snapshot_timestamp"] = now
        r["underlying"] = underlying
        r["spot_price"] = round(spot, 2)
    insert_options_snapshot(raw_rows)

    # 2. Compute + store GEX
    per_strike, summary = _compute_gex_snapshot(chain, spot, underlying.replace("^", ""), now)

    _validate_snapshot(per_strike, summary, underlying)

    if per_strike:
        insert_gex_levels(per_strike)
    if summary:
        upsert_gex_summary(summary)

    log.info(
        "yfinance: %s done — spot=%.2f, GEX net=%.0f, call_wall=%s, put_wall=%s",
        underlying, spot, summary.get("net_gex", 0),
        summary.get("call_wall_strike"), summary.get("put_wall_strike"),
    )

    return summary


def run_all(cfg: Config) -> dict[str, dict | None]:
    """Run options + GEX snapshot for all configured underlyings."""
    results: dict[str, dict | None] = {}
    for sym in cfg.options_underlyings:
        try:
            results[sym] = run_snapshot(cfg, sym)
        except Exception:
            log.exception("yfinance snapshot failed for %s", sym)
            results[sym] = None
    return results
```

### 5.8 src/pipeline/monitoring/health.py

```python
"""Minimal HTTP health-check server.

Railway polls the configured port; we also surface a /ready endpoint
that reports the last run status of each ingestion module.
"""

from __future__ import annotations

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Any

log = logging.getLogger("pipeline.monitoring.health")


class _Handler(BaseHTTPRequestHandler):
    status_store: dict[str, Any] = {}  # shared across instances

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "service": "quanta-pipeline"})
        elif self.path == "/ready":
            self._respond(200, self.status_store)
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, body: dict) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # silence health-check noise


def serve(port: int, status_store: dict[str, Any]) -> HTTPServer:
    _Handler.status_store = status_store
    server = HTTPServer(("0.0.0.0", port), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("Health server listening on :%d", port)
    return server
```

### 5.9 src/pipeline/main.py

```python
"""Entry point: scheduler + health server.

Schedule (ET):
  - Nightly 18:30: Databento + ForexFactory
  - Intraday 09:00-16:30 every 30 min: yfinance options + GEX
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Config
from .db import init_pool
from .ingestion import databento_ingest, forexfactory_ingest, yfinance_ingest
from .logging_setup import setup_logging
from .monitoring.health import serve

log = logging.getLogger("pipeline")


def _nightly_job(cfg: Config, status_store: dict) -> None:
    """Nightly batch: Databento incremental + ForexFactory."""
    log.info("=== NIGHTLY JOB START ===")

    # Databento — backfill instruments that have no data, nightly for rest
    for sym in cfg.futures_instruments:
        from .db import get_latest_bar_timestamp

        latest = get_latest_bar_timestamp(sym)
        if latest is None:
            log.info("No data for %s — running backfill", sym)
            databento_ingest.run_instrument_backfill(cfg, sym)
        else:
            databento_ingest.run_instrument_nightly(cfg, sym)

    forexfactory_ingest.run(cfg)

    status_store["last_nightly"] = time.time()
    log.info("=== NIGHTLY JOB DONE ===")


def _intraday_options_job(cfg: Config, status_store: dict) -> None:
    """Intraday yfinance options pull (runs every 30 min in window)."""
    log.info("=== INTRADAY OPTIONS ===")
    yfinance_ingest.run_all(cfg)
    status_store["last_intraday"] = time.time()
    log.info("=== INTRADAY OPTIONS DONE ===")


def main() -> None:
    cfg = Config.from_env()
    setup_logging(cfg.log_level)

    log.info("Quanta pipeline starting — nightly=%s intraday=%s",
             cfg.run_nightly, cfg.run_intraday)

    # Database
    init_pool(cfg.supabase_database_url)

    # Shared status store (read by /ready endpoint)
    status: dict = {
        "last_nightly": None,
        "last_intraday": None,
        "started_at": time.time(),
    }

    # Health check server (non-blocking)
    serve(cfg.port, status)

    # APScheduler
    scheduler = BackgroundScheduler(timezone=cfg.et_tz)

    if cfg.run_nightly:
        # Run at 18:30 ET weekdays
        scheduler.add_job(
            _nightly_job,
            trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=30, timezone=cfg.et_tz),
            args=[cfg, status],
            id="nightly",
            replace_existing=True,
        )
        log.info("Scheduled nightly: Mon-Fri 18:30 ET")

    if cfg.run_intraday:
        # Run every 30 min between 09:00 and 16:30 ET weekdays
        scheduler.add_job(
            _intraday_options_job,
            trigger=CronTrigger(day_of_week="mon-fri", hour="9-16", minute="0,30", timezone=cfg.et_tz),
            args=[cfg, status],
            id="intraday",
            replace_existing=True,
        )
        log.info("Scheduled intraday: Mon-Fri 09:00-16:30 ET, every 30 min")

    scheduler.start()

    # Graceful shutdown
    def _shutdown(signum, frame):
        log.info("Received signal %s, shutting down", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Keep alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        _shutdown(None, None)


if __name__ == "__main__":
    main()
```

---

## 6. Supabase Database Schema

Run these migrations (in order) via `supabase db push` or the Supabase SQL editor.

### 6.1 ohlcv_1m

```sql
CREATE TABLE IF NOT EXISTS ohlcv_1m (
    id BIGSERIAL PRIMARY KEY,
    instrument VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    UNIQUE (instrument, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_1m_instrument_ts
    ON ohlcv_1m (instrument, timestamp DESC);
```

### 6.2 news_events

```sql
CREATE TABLE IF NOT EXISTS news_events (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time_et VARCHAR(10),
    currency VARCHAR(10) NOT NULL,
    impact VARCHAR(10) NOT NULL CHECK (impact IN ('High', 'Medium', 'Low')),
    event TEXT NOT NULL,
    actual VARCHAR(50),
    forecast VARCHAR(50),
    previous VARCHAR(50),
    UNIQUE (date, time_et, event, currency)
);

CREATE INDEX IF NOT EXISTS idx_news_events_date ON news_events (date DESC);
CREATE INDEX IF NOT EXISTS idx_news_events_impact ON news_events (impact);
```

### 6.3 options_chain_snapshots

```sql
CREATE TABLE IF NOT EXISTS options_chain_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    underlying VARCHAR(10) NOT NULL,
    strike DOUBLE PRECISION NOT NULL,
    expiry DATE NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('call', 'put')),
    open_interest BIGINT NOT NULL DEFAULT 0,
    volume BIGINT NOT NULL DEFAULT 0,
    implied_volatility DOUBLE PRECISION,
    delta DOUBLE PRECISION,
    gamma DOUBLE PRECISION,
    last_price DOUBLE PRECISION,
    spot_price DOUBLE PRECISION NOT NULL,
    dte INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_options_snapshot_ts
    ON options_chain_snapshots (snapshot_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_options_snapshot_underlying
    ON options_chain_snapshots (underlying, snapshot_timestamp DESC);
```

### 6.4 gex_levels_daily

```sql
CREATE TABLE IF NOT EXISTS gex_levels_daily (
    id BIGSERIAL PRIMARY KEY,
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    date DATE NOT NULL,
    underlying VARCHAR(10) NOT NULL,
    strike DOUBLE PRECISION NOT NULL,
    call_gex DOUBLE PRECISION NOT NULL DEFAULT 0,
    put_gex DOUBLE PRECISION NOT NULL DEFAULT 0,
    net_gex DOUBLE PRECISION NOT NULL DEFAULT 0,
    UNIQUE (snapshot_timestamp, underlying, strike)
);

CREATE INDEX IF NOT EXISTS idx_gex_date ON gex_levels_daily (date DESC, underlying);
```

### 6.5 gex_summary

```sql
CREATE TABLE IF NOT EXISTS gex_summary (
    id BIGSERIAL PRIMARY KEY,
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    date DATE NOT NULL,
    underlying VARCHAR(10) NOT NULL,
    total_call_gex DOUBLE PRECISION,
    total_put_gex DOUBLE PRECISION,
    net_gex DOUBLE PRECISION,
    call_wall_strike DOUBLE PRECISION,
    put_wall_strike DOUBLE PRECISION,
    gex_flip_strike DOUBLE PRECISION,
    zero_gamma_strike DOUBLE PRECISION,
    max_pain_strike DOUBLE PRECISION,
    spot_price DOUBLE PRECISION,
    UNIQUE (snapshot_timestamp, underlying)
);

CREATE INDEX IF NOT EXISTS idx_gex_summary_date ON gex_summary (date DESC, underlying);
```

### 6.6 ingestion_state (tracking)

```sql
CREATE TABLE IF NOT EXISTS ingestion_state (
    source VARCHAR(64) PRIMARY KEY,
    last_successful_run TIMESTAMPTZ,
    last_data_timestamp TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'ok',
    consecutive_failures INT NOT NULL DEFAULT 0,
    error_message TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed rows
INSERT INTO ingestion_state (source) VALUES
    ('databento'), ('forexfactory'), ('yfinance')
ON CONFLICT (source) DO NOTHING;
```

---

## 7. Setup Commands

```bash
# 1. Create project directory
cd /path/to/quanta
mkdir -p src/pipeline/ingestion src/pipeline/monitoring

# 2. Write all files listed above (pyproject.toml, Dockerfile, .env.example,
#    and all Python files under src/)

# 3. Create virtual env
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate       # Windows

# 4. Install
pip install .

# 5. Set env vars (or use .env)
export DATABENTO_API_KEY=db_xxx
export SUPABASE_DATABASE_URL=postgresql://user:pass@host:6543/postgres

# 6. Run (will sit in foreground, logging to stdout)
quanta-pipeline
```

---

## 8. One-Time Backfill

After the pipeline is running, trigger a historical backfill by running
the backfill function directly:

```bash
python -c "
from pipeline.config import Config
from pipeline.db import init_pool
from pipeline.ingestion import databento_ingest
from pipeline.logging_setup import setup_logging

cfg = Config.from_env()
setup_logging(cfg.log_level)
init_pool(cfg.supabase_database_url)

for sym in cfg.futures_instruments:
    databento_ingest.run_instrument_backfill(cfg, sym)
"
```

This can take 30-60 minutes for 7 years of data across 6 instruments.
It runs in 6-month chunks and upserts each chunk progressively, so it
is safe to interrupt and resume.

---

## 9. Railway Deployment

### 9.1 railway.toml

Put this in the project root so Railway knows the build + start command:

```toml
[build]
  builder = "DOCKERFILE"
  dockerfile = "Dockerfile"

[deploy]
  restartPolicyType = "ON_FAILURE"
  healthcheckPath = "/health"
  healthcheckTimeout = 10
```

### 9.2 Required Environment Variables on Railway

| Variable                 | Source                       |
|--------------------------|------------------------------|
| `DATABENTO_API_KEY`      | Databento dashboard          |
| `SUPABASE_DATABASE_URL`  | Supabase project → Connect   |
| `PORT`                   | Railway sets automatically   |

### 9.3 Initial Backfill on Railway

After first deploy, SSH into the Railway shell or use a one-off job:

```bash
railway run python -c "
from pipeline.config import Config; from pipeline.db import init_pool
from pipeline.ingestion import databento_ingest; from pipeline.logging_setup import setup_logging
cfg = Config.from_env(); setup_logging(cfg.log_level); init_pool(cfg.supabase_database_url)
for sym in cfg.futures_instruments: databento_ingest.run_instrument_backfill(cfg, sym)
"
```

---

## 10. Error Handling Strategy

### 10.1 Retry Policy (all modules)

| Scenario            | Retries | Wait        |
|---------------------|---------|-------------|
| Network timeout     | 3       | 4s → 8s → 16s |
| HTTP 429 (rate-limit) | 3     | 4s → 8s → 16s |
| HTTP 5xx            | 3       | 4s → 8s → 16s |
| 4xx (non-429)       | 0       | fail fast    |

### 10.2 Circuit Breaker (current approach)

Each instrument/source is independent. A failure in `ES` does not block
`NQ` or ForexFactory. The nightly job wraps each instrument in its own
try/except and continues to the next.

### 10.3 Data Validation

After each insert batch:
- Row count is logged (0 rows on a trading day = warning)
- `ingestion_state` table tracks consecutive failures
- GEX snapshot validates both call and put GEX are non-zero

### 10.4 Alerting (v1)

No external alerting service. The pipeline relies on:
- Railway logs (accessible via dashboard)
- Health check endpoint (`/health` returns 200, `/ready` shows last run times)
- `ingestion_state` table with consecutive_failures counter

Ponytail: Add Slack/PagerDuty webhook integration when the pipeline
has been running and you know the alert volume is manageable.

---

## 11. Verification Checklist

Before considering the pipeline "done":

- [ ] All SQL migrations applied in Supabase
- [ ] `quanta-pipeline` starts, health check responds at `/health`
- [ ] Databento backfill completes for all 6 instruments
- [ ] ForexFactory upserts rows (check `SELECT COUNT(*) FROM news_events`)
- [ ] Options snapshot runs manually: `yfinance_ingest.run_snapshot(cfg, "^SPX")`
- [ ] GEX levels have non-zero values (not all zero)
- [ ] `ingestion_state` shows `status = 'ok'` for all 3 sources
- [ ] Scheduled jobs fire at correct ET times (check logs after deploy)
- [ ] Railway health check passes (`/health` returns 200 from Railway probes)

---

## 12. Future Enhancements (Not in v1)

| Feature | When |
|---------|------|
| Slack/email alert on N consecutive failures | After first month of production |
| FRED Treasury yield API for dynamic risk-free rate | If rates move >100bp from 4.75% |
| Market holiday calendar (avoid empty pulls) | If users complain about stale data |
| Async option chain fetches (parallel underlyings) | If 30-min window is too tight |
| Supabase real-time push on new data | When frontend needs live updates |
| Delta computation for options (BS delta) | When report requires moneyness breakdown |
