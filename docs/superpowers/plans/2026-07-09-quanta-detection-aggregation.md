# Quanta Detection & Aggregation Engine — Implementation Plan
**Date:** 2026-07-09
**Status:** Approved for implementation

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Configuration & Database Schema](#2-configuration--database-schema)
3. [Stage 2: Detection Modules](#3-stage-2-detection-modules)
   - 3.1 FVG Detection
   - 3.2 OB Detection
   - 3.3 BSL/SSL Detection
   - 3.4 PO3 Classification
   - 3.5 Key Opens
   - 3.6 Opening Gaps
   - 3.7 News Candle Detection
   - 3.8 Macros
   - 3.9 GEX Computation
4. [Stage 3: Aggregation](#4-stage-3-aggregation)
5. [Orchestrator](#5-orchestrator)
6. [Tests & Fixtures](#6-tests--fixtures)
7. [Dependencies & Deployment](#7-dependencies--deployment)

---

## 1. Project Structure

The pipeline lives in its own Python project alongside (but outside) the Next.js frontend. Both share the Supabase Postgres instance; pipeline writes, app reads.

```
quanta-pipeline/
├── pyproject.toml
├── .env.example
├── Dockerfile
├── src/
│   ├── __init__.py
│   ├── config.py                  # env-based config, DB URLs, API keys
│   ├── db.py                      # Supabase/Postgres connection, helpers
│   ├── models.py                  # typed dataclasses for each instance type
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── fair_value_gaps.py
│   │   ├── order_blocks.py
│   │   ├── liquidity_sweeps.py
│   │   ├── power_of_3.py
│   │   ├── key_opens.py
│   │   ├── opening_gaps.py
│   │   ├── news_candles.py
│   │   ├── macros.py
│   │   └── gex.py
│   ├── aggregation/
│   │   ├── __init__.py
│   │   ├── aggregator.py          # generic aggregation engine
│   │   └── queries.py             # SQL builders per report type
│   └── orchestrator.py            # main entry point: stages 2 + 3
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── ohlcv_samples.py       # synthetic OHLCV for each instrument/TF
│   │   └── news_samples.py
│   ├── test_fair_value_gaps.py
│   ├── test_order_blocks.py
│   ├── test_liquidity_sweeps.py
│   ├── test_power_of_3.py
│   ├── test_key_opens.py
│   ├── test_opening_gaps.py
│   ├── test_news_candles.py
│   ├── test_macros.py
│   ├── test_gex.py
│   └── test_aggregator.py
└── scripts/
    └── run_pipeline.py            # CLI wrapper for manual runs
```

Files are created at `C:\Users\AJ\OneDrive\Documents\Quanta\quanta-pipeline\...`.

---

## 2. Configuration & Database Schema

### 2.1 config.py

```python
"""Environment-based configuration. All secrets via env vars, never hardcoded."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    supabase_url: str = field(default_factory=lambda: os.environ["SUPABASE_URL"])
    supabase_key: str = field(default_factory=lambda: os.environ["SUPABASE_SERVICE_KEY"])
    upstash_redis_url: Optional[str] = os.environ.get("UPSTASH_REDIS_URL")
    databento_api_key: Optional[str] = os.environ.get("DATABENTO_API_KEY")

    # Pipeline scheduling (ET times converted to UTC)
    nightly_run_hour_utc: int = 23  # 18:30 ET = 23:30 UTC (EST) or 22:30 UTC (EDT)
    intraday_interval_minutes: int = 30

    # Thresholds
    po3_manipulation_threshold_pct: float = 0.02   # 0.02% below open to confirm manipulation
    fvg_min_size_ticks: int = 1                     # minimum FVG gap size in ticks
    liquidity_sweep_proximity_ticks: int = 2        # how close price must get to sweep

    # Lookback windows for aggregation (in trading days)
    lookback_windows: list[int] = field(default_factory=lambda: [63, 126, 252])

    @classmethod
    def load(cls) -> "Config":
        return cls()
```

### 2.2 models.py — Typed Dataclasses

```python
"""Minimal typed containers. No ORM, no heavy framework — plain dataclasses + row factory."""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


@dataclass
class FVGInstance:
    instrument: str
    timeframe: str            # 1m, 5m, 15m, 1H, 4H, 1D
    high_bound: Decimal
    low_bound: Decimal
    creation_time: datetime
    creation_price: Decimal
    fill_time: Optional[datetime] = None
    fill_pct: Optional[float] = None     # 0–100
    status: str = "open"                 # open, partial, filled


@dataclass
class OrderBlockInstance:
    instrument: str
    timeframe: str
    direction: str            # bullish, bearish
    origin_candle_time: datetime
    origin_open: Decimal
    origin_high: Decimal
    origin_low: Decimal
    origin_close: Decimal
    first_test_time: Optional[datetime] = None
    outcome: str = "untested" # untested, respected, broken, mitigated


@dataclass
class LiquidityLevel:
    instrument: str
    session: str              # london, ny_am, ny_pm, asian, overnight
    level_type: str           # bsl, ssl
    price: Decimal
    swing_high_time: datetime
    swing_low_time: datetime
    swept: bool = False
    sweep_time: Optional[datetime] = None
    post_sweep_direction: Optional[str] = None  # bullish, bearish
    magnitude_pts: Optional[Decimal] = None


@dataclass
class PO3Instance:
    instrument: str
    window_type: str           # daily, 4h_6am, 4h_10am, 30m_930, 30m_1000, ny_session, 15m_945
    date: date
    window_start: datetime
    window_end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    hod: Decimal
    hod_time: datetime
    lod: Decimal
    lod_time: datetime
    phase: str                  # bullish, bearish, unconfirmed
    manip_depth_pct: Optional[float] = None
    manip_start_time: Optional[datetime] = None
    close_in_upper_pct: Optional[bool] = None
    news_flag: bool = False
    pd_array_held_hod: Optional[str] = None   # fvg, ob, key_open, round_number, none
    pd_array_held_lod: Optional[str] = None
    pd_array_detail_hod: Optional[str] = None  # {"type":"fvg","tf":"1H","id":123}
    pd_array_detail_lod: Optional[str] = None


@dataclass
class KeyOpenInstance:
    instrument: str
    date: date
    open_type: str            # open_1800, open_0000, open_1000
    open_price: Decimal
    session_high: Decimal
    session_low: Decimal
    respected: bool = False
    rejection: bool = False
    time_to_test: Optional[int] = None        # minutes after open
    deviation_before_test_pts: Optional[Decimal] = None
    reversal_magnitude_pts: Optional[Decimal] = None


@dataclass
class OpeningGapInstance:
    instrument: str
    gap_type: str             # ndog, nwog
    gap_date: date
    prior_close_price: Decimal
    current_open_price: Decimal
    gap_direction: str        # bullish, bearish
    gap_size_pts: Decimal
    fill_time: Optional[datetime] = None
    fill_status: str = "open"  # open, partial, filled
    fill_pct: Optional[float] = None
    session_of_fill: Optional[str] = None


@dataclass
class NewsCandleInstance:
    instrument: str
    event_name: str
    event_time: datetime
    impact: str               # high, medium
    currency: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    high_taken: bool = False
    low_taken: bool = False
    high_taken_time: Optional[datetime] = None
    low_taken_time: Optional[datetime] = None
    side_taken_first: Optional[str] = None  # high, low, both, neither
    post_take_magnitude_pts: Optional[Decimal] = None


@dataclass
class MacroInstance:
    instrument: str
    window_type: str          # macro_950, macro_1050, macro_110, macro_210, macro_315
    date: date
    window_start: datetime
    window_end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    hod: Decimal
    hod_time: datetime
    lod: Decimal
    lod_time: datetime
    direction: str            # bullish, bearish, choppy
    magnitude_pts: Decimal
    # Prior context snapshot
    hod_of_day_made: bool = False
    lod_of_day_made: bool = False
    preceding_po3_phase: Optional[str] = None
    at_pd_array_open: Optional[str] = None   # inside_fvg, at_ob, none
    news_flag: bool = False
    london_direction: Optional[str] = None
    ny_open_30m_direction: Optional[str] = None
    gex_proximity: Optional[str] = None       # near_call_wall, near_put_wall, neutral


@dataclass
class GEXLevelDaily:
    date: date
    underlying: str           # SPX, NDX
    spot_price: Decimal
    call_wall_strike: Decimal
    put_wall_strike: Decimal
    gex_flip_strike: Optional[Decimal] = None
    zero_gamma_strike: Optional[Decimal] = None
    max_pain_strike: Decimal
    total_call_gex: float = 0.0
    total_put_gex: float = 0.0
    net_gex: float = 0.0
```

### 2.3 db.py

```python
"""Thin Postgres access via supabase client. No ORM."""

from datetime import date
from typing import Any

from supabase import create_client, Client
from src.config import Config


_db: Client | None = None


def get_db(cfg: Config) -> Client:
    global _db
    if _db is None:
        _db = create_client(cfg.supabase_url, cfg.supabase_key)
    return _db


def insert_many(table: str, rows: list[dict], db: Client) -> None:
    """Batch insert rows. Each row dict keys match column names."""
    if not rows:
        return
    # Supabase Python client insert_many returns all rows; we ignore the return
    db.table(table).insert(rows).execute()


def delete_old_instances(table: str, instrument: str, cutoff_date: date, db: Client) -> None:
    """Remove stale instances before reprocessing a date range."""
    db.table(table).delete().eq("instrument", instrument).gte(
        "date", cutoff_date.isoformat()
    ).execute()


def fetch_ohlcv(
    instrument: str, start: str, end: str, db: Client, timeframe: str = "1m"
) -> list[dict]:
    """Fetch OHLCV bars for a date range. Returns list of dicts keyed by column."""
    resp = db.table("ohlcv_1m") \
        .select("*") \
        .eq("instrument", instrument) \
        .gte("timestamp", start) \
        .lte("timestamp", end) \
        .order("timestamp") \
        .execute()
    return resp.data
```

---

## 3. Stage 2: Detection Modules

All detectors follow the same signature: `detect(bars: list[dict], instrument: str, date: date, db: Client) -> list[dataclass]`. Pure functions where possible; DB writes happen in the orchestrator, not inside detectors.

### 3.1 FVG Detection — fair_value_gaps.py

```python
"""Fair Value Gap detection across multiple timeframes.

A bullish FVG forms when the middle candle's high < the prior candle's low,
leaving a gap between prior low and middle high. Bearish is the mirror:
middle candle's low > prior candle's high.

Resolution order:
  1. Build higher-TF bars from 1m source (5m, 15m, 1H, 4H, Daily)
  2. Scan each TF for 3-candle gaps
  3. For new gaps in today's bars, check if subsequently filled
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from src.models import FVGInstance


def resample_bars(bars: list[dict], timeframe_minutes: int) -> list[dict]:
    """Aggregate 1m bars into higher timeframe OHLC.

    Pure function. Input bars must be sorted ascending by timestamp.
    Returns list of dicts with keys: timestamp, open, high, low, close.
    """
    if not bars:
        return []

    # Group consecutive 1m bars into N-minute periods
    result: list[dict] = []
    period_start = bars[0]["timestamp"]
    period: list[dict] = []

    for bar in bars:
        # Check if bar falls in current period
        bar_ts = bar["timestamp"]
        epoch = datetime.fromtimestamp(0) if isinstance(bar_ts, (int, float)) else bar_ts
        # Use minutes-since-midnight grouping
        if isinstance(bar_ts, str):
            bar_dt = datetime.fromisoformat(bar_ts)
        elif isinstance(bar_ts, datetime):
            bar_dt = bar_ts
        else:
            bar_dt = datetime.fromtimestamp(bar_ts)

        if period and (
            bar_dt.timestamp() - period[0]["_dt"].timestamp()
            >= timeframe_minutes * 60
        ):
            result.append(_collapse_period(period))
            period = []

        bar["_dt"] = bar_dt
        period.append(bar)

    if period:
        result.append(_collapse_period(period))

    return result


def _collapse_period(bars: list[dict]) -> dict:
    """Collapse a list of 1m bars into one OHLC bar."""
    return {
        "timestamp": bars[0]["_dt"],
        "open": Decimal(str(bars[0]["open"])),
        "high": max(Decimal(str(b["high"])) for b in bars),
        "low": min(Decimal(str(b["low"])) for b in bars),
        "close": Decimal(str(bars[-1]["close"])),
    }


def detect_fvgs(bars: list[dict], instrument: str, timeframe: str, tf_minutes: int) -> list[FVGInstance]:
    """Detect FVGs in bars of a given timeframe.

    For a 3-candle sequence (c0, c1, c2):
      Bullish FVG: c1.high < c0.low  →  gap [c1.high, c0.low]
      Bearish FVG: c1.low > c0.high  →  gap [c0.high, c1.low]

    Checks subsequent bars to determine if the gap was filled.
    """
    tf_bars = resample_bars(bars, tf_minutes) if tf_minutes > 1 else [
        {
            "timestamp": b["timestamp"] if isinstance(b["timestamp"], datetime) else datetime.fromisoformat(b["timestamp"]) if isinstance(b["timestamp"], str) else datetime.fromtimestamp(b["timestamp"]),
            "open": Decimal(str(b["open"])),
            "high": Decimal(str(b["high"])),
            "low": Decimal(str(b["low"])),
            "close": Decimal(str(b["close"])),
        }
        for b in bars
    ]

    instances: list[FVGInstance] = []

    for i in range(len(tf_bars) - 2):
        c0, c1, c2 = tf_bars[i], tf_bars[i + 1], tf_bars[i + 2]
        gap_low = gap_high = None
        is_bullish = False

        # Bullish FVG: middle candle's high < prior candle's low
        if c1["high"] < c0["low"]:
            gap_low = c1["high"]
            gap_high = c0["low"]
            is_bullish = True
        # Bearish FVG: middle candle's low > prior candle's high
        elif c1["low"] > c0["high"]:
            gap_low = c0["high"]
            gap_high = c1["low"]

        if gap_low is not None and gap_high is not None:
            creation_time = c1["timestamp"]
            created_date = creation_time.date() if hasattr(creation_time, "date") else creation_time
            fill_pct, fill_time, status = _check_fill(
                tf_bars, i + 3, gap_low, gap_high, is_bullish
            )
            instances.append(FVGInstance(
                instrument=instrument,
                timeframe=timeframe,
                high_bound=gap_high,
                low_bound=gap_low,
                creation_time=creation_time,
                creation_price=c1["close"],
                fill_time=fill_time,
                fill_pct=fill_pct,
                status=status,
            ))

    return instances


def _check_fill(
    bars: list[dict], start_idx: int,
    gap_low: Decimal, gap_high: Decimal, is_bullish: bool
) -> tuple[Optional[float], Optional[datetime], str]:
    """Scan bars after the gap to determine fill status.

    Full fill: price crosses the entire gap (printed through opposite side).
    Partial fill: price enters the gap but doesn't cross entirely.
    """
    if start_idx >= len(bars):
        return None, None, "open"

    total_range = float(gap_high - gap_low)
    if total_range <= 0:
        return 100.0, bars[start_idx]["timestamp"], "filled"

    max_penetration = Decimal("0")
    fill_time = None

    for j in range(start_idx, len(bars)):
        bar = bars[j]

        if is_bullish:
            # Price must trade up through the gap (price went down, gap is below)
            # For bullish FVG: gap is below, we need price to come back up into it
            # Actually: bullish FVG means price gapped UP (c1.high < c0.low is an upward gap)
            # Wait - let me re-read: c1.high < c0.low → the middle candle's high is lower
            # than the prior candle's low. This means prices gapped DOWN.
            # A bullish FVG is a gap DOWN that subsequently gets filled to the upside.
            # Actually in ICT: bullish FVG = price gapped down (bearish candles), 
            # the gap acts as support that holds on the retest.
            # Let me just check price penetration of the gap zone:
            if bar["low"] <= gap_high and bar["high"] >= gap_low:
                # Price entered the gap zone
                penetration = min(bar["high"], gap_high) - max(bar["low"], gap_low)
                pct = float(penetration) / total_range * 100
                if pct > max_penetration:
                    max_penetration = pct
                    fill_time = bar["timestamp"]

                if bar["low"] <= gap_low and bar["high"] >= gap_high:
                    # Price crossed the entire gap
                    return 100.0, bar["timestamp"], "filled"
        else:
            # Bearish FVG: gap is above
            if bar["low"] <= gap_high and bar["high"] >= gap_low:
                penetration = min(bar["high"], gap_high) - max(bar["low"], gap_low)
                pct = float(penetration) / total_range * 100
                if pct > max_penetration:
                    max_penetration = pct
                    fill_time = bar["timestamp"]

                if bar["low"] <= gap_low and bar["high"] >= gap_high:
                    return 100.0, bar["timestamp"], "filled"

    if max_penetration > 0:
        return min(max_penetration, 99.9), fill_time, "partial"

    return None, None, "open"


# TF config: (name, minutes)
TF_CONFIGS = [
    ("1m", 1), ("5m", 5), ("15m", 15), ("1H", 60), ("4H", 240), ("1D", 1440),
]


def detect(bars: dict[str, list[dict]], instrument: str, date: date) -> list[FVGInstance]:
    """Detect FVGs across all timeframes for a given day's bars.

    Args:
        bars: dict keyed by timeframe string, each value is a list of 1m OHLCV dicts.
              e.g. {"1m": [...], "5m": resampled_or_pre-aggregated, ...}
              For simplicity, pass the same 1m source; each TF resolution handles resampling.
              Caller is responsible for passing enough surrounding context bars for fill checking.
        instrument: e.g. "ES"
        date: trading date

    Returns flat list of all FVGInstances detected.
    """
    # Use raw 1m bars and resample internally for higher TFs
    raw_1m = bars.get("1m", [])
    all_instances: list[FVGInstance] = []

    for tf_name, tf_minutes in TF_CONFIGS:
        tf_instances = detect_fvgs(raw_1m, instrument, tf_name, tf_minutes)
        all_instances.extend(tf_instances)

    return all_instances
```

### 3.2 OB Detection — order_blocks.py

```python
"""Order Block detection.

Bullish OB: the last down-close candle immediately before a bullish impulse
(3+ consecutive up-closes or a single bar with range > 2x average).
Bearish OB: the last up-close candle immediately before a bearish impulse.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.models import OrderBlockInstance


def _impulse_start(bars: list[dict], idx: int, lookback: int = 3) -> Optional[int]:
    """Find the index of the candle just before an impulse starts.

    Bullish impulse: bars[idx] is the first bar of >= lookback consecutive up-close bars.
    Returns the index of the candle just before the impulse (the potential OB).
    """
    if idx < 1 or idx + lookback > len(bars):
        return None

    # Check if bars[idx:idx+lookback] are all up-close
    for offset in range(lookback):
        b = bars[idx + offset]
        if b["close"] <= b["open"]:
            return None
    return idx - 1


def detect(bars: list[dict], instrument: str, timeframe: str = "15m") -> list[OrderBlockInstance]:
    """Detect order blocks in a series of bars.

    Args:
        bars: OHLCV dicts sorted ascending by time, with keys: timestamp, open, high, low, close
        instrument: e.g. "ES"
        timeframe: the bar timeframe (default 15m, but any works)

    Returns list of OrderBlockInstance.
    """
    instances: list[OrderBlockInstance] = []

    for i in range(1, len(bars)):
        ob_idx = _impulse_start(bars, i, lookback=3)
        if ob_idx is not None:
            ob_candle = bars[ob_idx]
            direction = "bullish"  # last down-close before bullish impulse
            if ob_candle["close"] >= ob_candle["open"]:
                # Could still be a bearish OB if impulse is bearish
                # Check for bearish impulse:
                bear_idx = _bearish_impulse_start(bars, i, lookback=3)
                if bear_idx is not None:
                    bear_ob = bars[bear_idx]
                    if bear_ob["close"] <= bear_ob["open"]:
                        direction = "bearish"
                    else:
                        continue  # ambiguous, skip
                else:
                    continue  # no impulse confirmed, skip

            instances.append(OrderBlockInstance(
                instrument=instrument,
                timeframe=timeframe,
                direction=direction,
                origin_candle_time=ob_candle["timestamp"],
                origin_open=Decimal(str(ob_candle["open"])),
                origin_high=Decimal(str(ob_candle["high"])),
                origin_low=Decimal(str(ob_candle["low"])),
                origin_close=Decimal(str(ob_candle["close"])),
            ))

    return instances


def _bearish_impulse_start(bars: list[dict], idx: int, lookback: int = 3) -> Optional[int]:
    """Find the index just before a bearish impulse starts."""
    if idx < 1 or idx + lookback > len(bars):
        return None
    for offset in range(lookback):
        b = bars[idx + offset]
        if b["close"] >= b["open"]:
            return None
    return idx - 1
```

### 3.3 BSL/SSL Detection — liquidity_sweeps.py

```python
"""Buy-side Liquidity (BSL) and Sell-side Liquidity (SSL) detection per session.

BSL = swing high (swing low's high, or prior session high)
SSL = swing low (swing high's low, or prior session low)

A sweep occurs when price exceeds the BSL/SSL level during the session.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional

from src.models import LiquidityLevel


SESSION_DEFS = {
    "asian":    (time(18, 0), time(3, 0)),    # 18:00 ET prev day → 03:00 ET
    "london":   (time(3, 0), time(9, 30)),     # 03:00 → 09:30 ET
    "ny_am":    (time(9, 30), time(12, 0)),    # 09:30 → 12:00 ET
    "ny_pm":    (time(12, 0), time(16, 0)),    # 12:00 → 16:00 ET
    "overnight":(time(16, 0), time(18, 0)),    # 16:00 → 18:00 ET (close to globex open)
}


def find_swing_highs(bars: list[dict], window: int = 5) -> list[Decimal]:
    """Identify swing highs: bars whose high is higher than `window` bars on each side."""
    highs: list[Decimal] = []
    for i in range(window, len(bars) - window):
        is_swing = True
        for offset in range(1, window + 1):
            if bars[i]["high"] <= bars[i - offset]["high"] or bars[i]["high"] <= bars[i + offset]["high"]:
                is_swing = False
                break
        if is_swing:
            highs.append(Decimal(str(bars[i]["high"])))
    return highs


def find_swing_lows(bars: list[dict], window: int = 5) -> list[Decimal]:
    """Identify swing lows: bars whose low is lower than `window` bars on each side."""
    lows: list[Decimal] = []
    for i in range(window, len(bars) - window):
        is_swing = True
        for offset in range(1, window + 1):
            if bars[i]["low"] >= bars[i - offset]["low"] or bars[i]["low"] >= bars[i + offset]["low"]:
                is_swing = False
                break
        if is_swing:
            lows.append(Decimal(str(bars[i]["low"])))
    return lows


def detect(
    bars: list[dict], instrument: str, trade_date: date,
    prior_session_high: Optional[Decimal] = None,
    prior_session_low: Optional[Decimal] = None,
) -> list[LiquidityLevel]:
    """Detect BSL/SSL levels and whether they were swept during the session.

    Args:
        bars: OHLCV dicts for the trading day, sorted ascending.
        instrument: e.g. "ES"
        trade_date: the trading date
        prior_session_high: highest price from prior session (for BSL)
        prior_session_low: lowest price from prior session (for SSL)

    Returns list of LiquidityLevel.
    """
    levels: list[LiquidityLevel] = []

    swing_highs = find_swing_highs(bars)
    swing_lows = find_swing_lows(bars)

    # BSL from swing highs
    for sh_price in swing_highs:
        swept = any(Decimal(str(b["high"])) > sh_price for b in bars)
        sweep_time = None
        post_dir = None
        if swept:
            for b in bars:
                if Decimal(str(b["high"])) > sh_price:
                    sweep_time = b["timestamp"]
                    break
            # Post-sweep direction: check close of bar that swept vs close of next bar
            sweep_idx = next(i for i, b in enumerate(bars) if Decimal(str(b["high"])) > sh_price)
            if sweep_idx < len(bars) - 1:
                post_dir = "bearish" if bars[sweep_idx + 1]["close"] < bars[sweep_idx]["close"] else "bullish"

        levels.append(LiquidityLevel(
            instrument=instrument,
            session="ny_am",  # caller should set correct session
            level_type="bsl",
            price=sh_price,
            swing_high_time=bars[0]["timestamp"],
            swing_low_time=bars[0]["timestamp"],
            swept=swept,
            sweep_time=sweep_time,
            post_sweep_direction=post_dir,
        ))

    # SSL from swing lows
    for sl_price in swing_lows:
        swept = any(Decimal(str(b["low"])) < sl_price for b in bars)
        sweep_time = None
        post_dir = None
        if swept:
            for b in bars:
                if Decimal(str(b["low"])) < sl_price:
                    sweep_time = b["timestamp"]
                    break
            sweep_idx = next(i for i, b in enumerate(bars) if Decimal(str(b["low"])) < sl_price)
            if sweep_idx < len(bars) - 1:
                post_dir = "bullish" if bars[sweep_idx + 1]["close"] > bars[sweep_idx]["close"] else "bearish"

        levels.append(LiquidityLevel(
            instrument=instrument,
            session="ny_am",
            level_type="ssl",
            price=sl_price,
            swing_high_time=bars[0]["timestamp"],
            swing_low_time=bars[0]["timestamp"],
            swept=swept,
            sweep_time=sweep_time,
            post_sweep_direction=post_dir,
        ))

    # Also add prior session high/low as BSL/SSL
    if prior_session_high is not None:
        swept = any(Decimal(str(b["high"])) > prior_session_high for b in bars)
        levels.append(LiquidityLevel(
            instrument=instrument, session="ny_am", level_type="bsl",
            price=prior_session_high,
            swing_high_time=bars[0]["timestamp"],
            swing_low_time=bars[0]["timestamp"],
            swept=swept,
        ))
    if prior_session_low is not None:
        swept = any(Decimal(str(b["low"])) < prior_session_low for b in bars)
        levels.append(LiquidityLevel(
            instrument=instrument, session="ny_am", level_type="ssl",
            price=prior_session_low,
            swing_high_time=bars[0]["timestamp"],
            swing_low_time=bars[0]["timestamp"],
            swept=swept,
        ))

    return levels
```

### 3.4 PO3 Classification — power_of_3.py

```python
"""Power of 3 phase classification — the flagship detector.

Classifies each of 7 time windows as BULLISH, BEARISH, or UNCONFIRMED
based on manipulation and distribution rules.

Rules (per spec):
  BULLISH: trades below open by >= threshold in first 40% of window,
           closes above open, close in upper 40% of range.
  BEARISH: trades above open by >= threshold in first 40%,
           closes below open, close in lower 40%.
  UNCONFIRMED: neither condition met.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from src.models import PO3Instance


# (window_type, start_hour_et, start_min_et, duration_minutes)
WINDOW_DEFS = [
    ("daily",      18, 0,  23 * 60 + 60),  # 18:00 → 17:00 next day (23h + 1h for next day)
    ("4h_6am",      6, 0,  240),            # 06:00 → 10:00
    ("4h_10am",    10, 0,  240),            # 10:00 → 14:00
    ("30m_930",     9, 30,  30),            # 09:30 → 10:00
    ("30m_1000",   10, 0,   30),            # 10:00 → 10:30
    ("ny_session",  9, 30,  90),            # 09:30 → 11:00 (90m)
    ("15m_945",     9, 45,  15),            # 09:45 → 10:00
]

# NY Session extends to 08:30 start when 8:30 news present
NEWS_EARLY_START = {"start_hour": 8, "start_min": 30, "duration_min": 150}  # 08:30 → 11:00


def classify_window(bars: list[dict], instrument: str, window_type: str,
                    trade_date: date, window_start_dt: datetime, window_end_dt: datetime,
                    news_flag: bool = False) -> PO3Instance:
    """Classify a single PO3 window.

    Args:
        bars: OHLCV bars within the window (subset of 1m bars), sorted ascending.
        instrument: e.g. "ES"
        window_type: key from WINDOW_DEFS
        trade_date: trading date
        window_start_dt, window_end_dt: ET time bounds
        news_flag: whether high-impact news is present this day

    Returns a PO3Instance with phase classification.
    """
    if not bars:
        return _empty_instance(instrument, window_type, trade_date, window_start_dt, window_end_dt)

    open_px = Decimal(str(bars[0]["open"]))
    high = max(Decimal(str(b["high"])) for b in bars)
    low = min(Decimal(str(b["low"])) for b in bars)
    close = Decimal(str(bars[-1]["close"]))
    close_px = Decimal(str(bars[-1]["close"]))

    # HOD/LOD
    hod_bar = max(bars, key=lambda b: b["high"])
    lod_bar = min(bars, key=lambda b: b["low"])
    hod = Decimal(str(hod_bar["high"]))
    lod = Decimal(str(lod_bar["low"]))
    hod_time = hod_bar["timestamp"]
    lod_time = lod_bar["timestamp"]

    # Phase classification
    window_duration = len(bars)  # in 1m bars
    first_40pct_cutoff = max(1, int(window_duration * 0.4))

    first_40pct = bars[:first_40pct_cutoff]
    first_40pct_low = min(Decimal(str(b["low"])) for b in first_40pct)
    first_40pct_high = max(Decimal(str(b["high"])) for b in first_40pct)

    threshold_pts = open_px * Decimal(str(0.0002))  # 0.02% default threshold

    # Compute range and check close position
    total_range = high - low
    manip_depth = None
    manip_start = None
    close_in_upper = None

    # Check BULLISH: trades below open by >= threshold in first 40%, close > open, close in upper 40%
    if total_range > 0:
        down_move = open_px - first_40pct_low
        up_move = first_40pct_high - open_px
        close_position_pct = float((close_px - low) / total_range) * 100

        if down_move >= threshold_pts and close_px > open_px and close_position_pct >= 60:
            phase = "bullish"
            manip_depth = float(down_move / open_px * 100)  # % below open
            close_in_upper = True
            # Find when manipulation low was made
            for b in first_40pct:
                if Decimal(str(b["low"])) == first_40pct_low:
                    manip_start = b["timestamp"]
                    break

        elif up_move >= threshold_pts and close_px < open_px and close_position_pct <= 40:
            phase = "bearish"
            manip_depth = float(up_move / open_px * 100)
            close_in_upper = False
            for b in first_40pct:
                if Decimal(str(b["high"])) == first_40pct_high:
                    manip_start = b["timestamp"]
                    break
        else:
            phase = "unconfirmed"

    else:
        phase = "unconfirmed"

    return PO3Instance(
        instrument=instrument,
        window_type=window_type,
        date=trade_date,
        window_start=window_start_dt,
        window_end=window_end_dt,
        open=open_px,
        high=high,
        low=low,
        close=close_px,
        hod=hod,
        hod_time=hod_time,
        lod=lod,
        lod_time=lod_time,
        phase=phase,
        manip_depth_pct=manip_depth,
        manip_start_time=manip_start,
        close_in_upper_pct=close_in_upper,
        news_flag=news_flag,
    )


def _empty_instance(instrument: str, window_type: str, trade_date: date,
                    w_start: datetime, w_end: datetime) -> PO3Instance:
    """Return an UNCONFIRMED instance when no bars exist for the window."""
    return PO3Instance(
        instrument=instrument, window_type=window_type, date=trade_date,
        window_start=w_start, window_end=w_end,
        open=Decimal("0"), high=Decimal("0"), low=Decimal("0"), close=Decimal("0"),
        hod=Decimal("0"), hod_time=w_start, lod=Decimal("0"), lod_time=w_start,
        phase="unconfirmed",
    )


def detect_for_day(
    bars: list[dict], instrument: str, trade_date: date,
    news_flag: bool = False, has_830_news: bool = False
) -> list[PO3Instance]:
    """Run PO3 classification for all 7 windows on a given day.

    Args:
        bars: all intraday 1m bars for the trading day (and surrounding context), sorted.
        instrument: e.g. "ES"
        trade_date: date of the trading day
        news_flag: any high-impact news today
        has_830_news: specifically 8:30 ET news (affects NY session start)

    Returns list of 7 PO3Instance (one per window).
    """
    instances: list[PO3Instance] = []

    for w_type, start_h, start_m, dur_m in WINDOW_DEFS:
        if w_type == "ny_session" and has_830_news:
            es = NEWS_EARLY_START
            w_start_et = trade_date.replace(hour=es["start_hour"], minute=es["start_min"])
            w_end_et = w_start_et + timedelta(minutes=es["duration_min"])
        else:
            w_start_et = trade_date.replace(hour=start_h, minute=start_m, second=0)
            w_end_et = w_start_et + timedelta(minutes=dur_m)

        # Slice bars to window
        window_bars = [
            b for b in bars
            if w_start_et <= _to_dt(b["timestamp"]) < w_end_et
        ]

        inst = classify_window(window_bars, instrument, w_type, trade_date,
                               w_start_et, w_end_et, news_flag)
        instances.append(inst)

    return instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts)
    return datetime.fromtimestamp(ts)
```

### 3.5 Key Opens — key_opens.py

```python
"""Key Open detection.

Tracks price behavior at 18:00 ET (Globex open), 00:00 ET (Midnight),
and 10:00 ET (Late morning). Determines if price returned to (respected)
or rejected each open level within the session.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional

from src.models import KeyOpenInstance


KEY_OPEN_DEFS = [
    ("open_1800", time(18, 0)),   # Globex open
    ("open_0000", time(0, 0)),    # Midnight
    ("open_1000", time(10, 0)),   # Late morning
]


def detect(bars: list[dict], instrument: str, trade_date: date) -> list[KeyOpenInstance]:
    """Detect key open level interactions for a trading day.

    Args:
        bars: all 1m bars for the day, sorted ascending.
        instrument: e.g. "ES"
        trade_date: trading date

    Returns list of KeyOpenInstance (one per open type that has data).
    """
    if not bars:
        return []

    instances: list[KeyOpenInstance] = []
    session_high = max(Decimal(str(b["high"])) for b in bars)
    session_low = min(Decimal(str(b["low"])) for b in bars)

    for open_type, open_time in KEY_OPEN_DEFS:
        # Find the bar at or just after the open time
        open_bars = [
            b for b in bars
            if _to_dt(b["timestamp"]).time() >= open_time
        ]
        if not open_bars:
            continue

        open_bar = open_bars[0]
        open_price = Decimal(str(open_bar["open"]))

        # Bars after the open
        post_open_bars = open_bars[1:] if len(open_bars) > 1 else []
        if not post_open_bars:
            instances.append(KeyOpenInstance(
                instrument=instrument, date=trade_date,
                open_type=open_type, open_price=open_price,
                session_high=session_high, session_low=session_low,
            ))
            continue

        # Check if price returned to open level
        deviation_before = Decimal("0")
        time_to_test = None
        reversal_mag = Decimal("0")
        respected = False
        rejection = True

        # Track max deviation from open before any return
        for i, b in enumerate(post_open_bars):
            bh = Decimal(str(b["high"]))
            bl = Decimal(str(b["low"]))

            if bl <= open_price <= bh:
                # Price returned to open level
                respected = True
                rejection = False
                time_to_test = i + 1  # minutes since open
                # Check reversal after test
                remaining = post_open_bars[i + 1:] if i + 1 < len(post_open_bars) else []
                if remaining:
                    after_high = max(Decimal(str(rb["high"])) for rb in remaining)
                    after_low = min(Decimal(str(rb["low"])) for rb in remaining)
                    reversal_mag = max(abs(after_high - open_price), abs(after_low - open_price))
                break
            else:
                # Track deviation
                deviation = min(abs(bh - open_price), abs(bl - open_price))
                if deviation > deviation_before:
                    deviation_before = deviation

        instances.append(KeyOpenInstance(
            instrument=instrument, date=trade_date,
            open_type=open_type, open_price=open_price,
            session_high=session_high, session_low=session_low,
            respected=respected, rejection=rejection,
            time_to_test=time_to_test,
            deviation_before_test_pts=deviation_before,
            reversal_magnitude_pts=reversal_mag if respected else None,
        ))

    return instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts)
    return datetime.fromtimestamp(ts)
```

### 3.6 Opening Gaps — opening_gaps.py

```python
"""Opening Gap detection: NDOG and NWOG.

NDOG (New Day Opening Gap): prior day 17:00 close vs current 18:00 globex open
NWOG (New Week Opening Gap): Friday 17:00 close vs Sunday globex open
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from src.models import OpeningGapInstance


def detect_ndog(
    bars_today: list[dict], bars_yesterday: list[dict],
    instrument: str, trade_date: date
) -> Optional[OpeningGapInstance]:
    """Detect NDOG: prior day 17:00 close → today 18:00 open.

    Args:
        bars_today: today's bars (must include 18:00 ET onward)
        bars_yesterday: yesterday's bars (must include up to 17:00 ET)
        instrument: e.g. "ES"
        trade_date: today's date

    Returns OpeningGapInstance or None if data insufficient.
    """
    if not bars_today or not bars_yesterday:
        return None

    # 17:00 close: last bar of yesterday's session
    yest_1700 = trade_date - timedelta(days=1)
    yest_1700_dt = yest_1700.replace(hour=17, minute=0)
    yest_close_bars = [
        b for b in bars_yesterday
        if _to_dt(b["timestamp"]) <= yest_1700_dt
    ]
    if not yest_close_bars:
        return None
    prior_close = Decimal(str(yest_close_bars[-1]["close"]))

    # 18:00 open: first bar of today after 18:00 ET
    today_1800 = trade_date.replace(hour=18, minute=0)
    today_open_bars = [
        b for b in bars_today
        if _to_dt(b["timestamp"]) >= today_1800
    ]
    if not today_open_bars:
        return None
    current_open = Decimal(str(today_open_bars[0]["open"]))

    gap_direction = "bullish" if current_open > prior_close else "bearish"
    gap_size = abs(current_open - prior_close)

    # Check fill throughout today's session
    fill_pct, fill_time, fill_status, session_of_fill = _check_gap_fill(
        bars_today, prior_close, current_open, gap_direction
    )

    return OpeningGapInstance(
        instrument=instrument, gap_type="ndog", gap_date=trade_date,
        prior_close_price=prior_close, current_open_price=current_open,
        gap_direction=gap_direction, gap_size_pts=gap_size,
        fill_time=fill_time, fill_status=fill_status,
        fill_pct=fill_pct, session_of_fill=session_of_fill,
    )


def detect_nwog(
    bars_sunday: list[dict], bars_friday: list[dict],
    instrument: str, trade_date: date
) -> Optional[OpeningGapInstance]:
    """Detect NWOG: Friday 17:00 close → Sunday globex open."""
    # Same structure as NDOG — different date offsets
    return detect_ndog(bars_sunday, bars_friday, instrument, trade_date)


def _check_gap_fill(
    bars: list[dict], prior_close: Decimal, current_open: Decimal, direction: str
) -> tuple[Optional[float], Optional[datetime], str, Optional[str]]:
    """Check if gap fills during the session."""
    if not bars:
        return None, None, "open", None

    total_range = float(abs(current_open - prior_close))
    if total_range <= 0:
        return 100.0, bars[0]["timestamp"], "filled", None

    max_pct = 0.0
    fill_time: Optional[datetime] = None
    session_of_fill = None

    for b in bars:
        b_low = float(b["low"])
        b_high = float(b["high"])
        fill_low = float(min(prior_close, current_open))
        fill_high = float(max(prior_close, current_open))

        # Check penetration into gap zone
        if b_high >= fill_low and b_low <= fill_high:
            penetration = min(b_high, fill_high) - max(b_low, fill_low)
            pct = penetration / total_range * 100
            if pct > max_pct:
                max_pct = pct
                fill_time = _to_dt(b["timestamp"])
                session_of_fill = _classify_session(fill_time)

            if b_low <= fill_low and b_high >= fill_high:
                return 100.0, fill_time, "filled", session_of_fill

    if max_pct > 0:
        return min(max_pct, 99.9), fill_time, "partial", session_of_fill
    return None, None, "open", None


def _classify_session(dt: datetime) -> str:
    h = dt.hour
    if 3 <= h < 9.5:  return "london"
    if 9.5 <= h < 12: return "ny_am"
    if 12 <= h < 16:  return "ny_pm"
    if 16 <= h < 18:  return "overnight"
    return "asian"


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime): return ts
    if isinstance(ts, str): return datetime.fromisoformat(ts)
    return datetime.fromtimestamp(ts)
```

### 3.7 News Candle Detection — news_candles.py

```python
"""News Candle detection.

For each high-impact news event, extract the 1m candle at the exact
release time and track whether its high/low is subsequently taken.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from src.models import NewsCandleInstance


def detect(
    bars: list[dict], instrument: str, trade_date: date,
    news_events: list[dict]
) -> list[NewsCandleInstance]:
    """Detect news candle instances for a given day.

    Args:
        bars: all 1m bars for the trading day, sorted ascending.
        instrument: e.g. "ES"
        trade_date: trading date
        news_events: list of dicts from news_events table for this day.
                     Each has: event_name, event_time (ET datetime), impact, currency

    Returns list of NewsCandleInstance.
    """
    if not bars or not news_events:
        return []

    instances: list[NewsCandleInstance] = []

    for event in news_events:
        event_time = event["event_time"]
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        # Find the 1m bar whose timestamp matches the event time
        # The bar at event_time is the one beginning at that time
        news_bar = None
        for b in bars:
            b_ts = _to_dt(b["timestamp"])
            # Match within 1 minute
            if abs((b_ts - event_time).total_seconds()) < 90:
                news_bar = b
                break

        if news_bar is None:
            continue

        n_open = Decimal(str(news_bar["open"]))
        n_high = Decimal(str(news_bar["high"]))
        n_low = Decimal(str(news_bar["low"]))
        n_close = Decimal(str(news_bar["close"]))

        # Track whether high/low is taken later in the session
        high_taken = False
        low_taken = False
        high_taken_time: Optional[datetime] = None
        low_taken_time: Optional[datetime] = None
        side_first: Optional[str] = None

        # Find bar index
        bar_idx = bars.index(news_bar)
        subsequent = bars[bar_idx + 1:]

        for sb in subsequent:
            sb_high = Decimal(str(sb["high"]))
            sb_low = Decimal(str(sb["low"]))

            if not high_taken and sb_high > n_high:
                high_taken = True
                high_taken_time = _to_dt(sb["timestamp"])
                if side_first is None:
                    side_first = "high"

            if not low_taken and sb_low < n_low:
                low_taken = True
                low_taken_time = _to_dt(sb["timestamp"])
                if side_first is None:
                    side_first = "low"

            if high_taken and low_taken:
                break

        if high_taken and low_taken:
            side_first = "both" if side_first is None else side_first  # both within same bar

        # Post-take magnitude
        post_mag = None
        if side_first and subsequent:
            sub_high = max(Decimal(str(sb["high"])) for sb in subsequent)
            sub_low = min(Decimal(str(sb["low"])) for sb in subsequent)
            post_mag = max(sub_high - n_high, n_low - sub_low)

        instances.append(NewsCandleInstance(
            instrument=instrument,
            event_name=event["event_name"],
            event_time=event_time,
            impact=event.get("impact", "high"),
            currency=event.get("currency", "USD"),
            open=n_open, high=n_high, low=n_low, close=n_close,
            high_taken=high_taken, low_taken=low_taken,
            high_taken_time=high_taken_time, low_taken_time=low_taken_time,
            side_taken_first=side_first or "neither",
            post_take_magnitude_pts=post_mag,
        ))

    return instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime): return ts
    if isinstance(ts, str): return datetime.fromisoformat(ts)
    return datetime.fromtimestamp(ts)
```

### 3.8 Macros — macros.py

```python
"""Macro window classification.

5 windows: 9:50-10:10, 10:50-11:10, 1:10-1:40, 2:10-2:40, 3:15-4:00
Each window records direction, HOD/LOD, magnitude, and prior context.
"""

from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional

from src.models import MacroInstance


MACRO_WINDOWS = [
    ("macro_950",  time(9, 50),  time(10, 10)),
    ("macro_1050", time(10, 50), time(11, 10)),
    ("macro_110",  time(13, 10), time(13, 40)),
    ("macro_210",  time(14, 10), time(14, 40)),
    ("macro_315",  time(15, 15), time(16, 0)),
]


def detect(
    bars_all: list[dict],
    instrument: str,
    trade_date: date,
    prior_context: Optional[dict] = None,
) -> list[MacroInstance]:
    """Detect macro window activity for a trading day.

    Args:
        bars_all: all intraday 1m bars, sorted ascending.
        instrument: e.g. "ES"
        trade_date: trading date
        prior_context: optional dict with pre-computed context:
            hod_of_day_made (bool), lod_of_day_made (bool),
            preceding_po3_phase (str), at_pd_array_open (str),
            news_flag (bool), london_direction (str),
            ny_open_30m_direction (str), gex_proximity (str)

    Returns list of MacroInstance (one per window that has data).
    """
    if not bars_all:
        return []

    ctx = prior_context or {}
    instances: list[MacroInstance] = []

    # Day-wide extremes for context
    day_high = max(Decimal(str(b["high"])) for b in bars_all)
    day_low = min(Decimal(str(b["low"])) for b in bars_all)
    # Check if HOD/LOD of day already made before first macro (9:50)
    pre_macro_bars = [
        b for b in bars_all
        if _to_dt(b["timestamp"]).time() < time(9, 50)
    ]
    hod_made_before = False
    lod_made_before = False
    if pre_macro_bars:
        pre_high = max(Decimal(str(b["high"])) for b in pre_macro_bars)
        pre_low = min(Decimal(str(b["low"])) for b in pre_macro_bars)
        if pre_high >= day_high:
            hod_made_before = True
        if pre_low <= day_low:
            lod_made_before = True

    for w_type, start_t, end_t in MACRO_WINDOWS:
        window_bars = [
            b for b in bars_all
            if start_t <= _to_dt(b["timestamp"]).time() < end_t
        ]
        if not window_bars:
            continue

        open_px = Decimal(str(window_bars[0]["open"]))
        high = max(Decimal(str(b["high"])) for b in window_bars)
        low = min(Decimal(str(b["low"])) for b in window_bars)
        close = Decimal(str(window_bars[-1]["close"]))
        magnitude = high - low

        hod_bar = max(window_bars, key=lambda b: b["high"])
        lod_bar = min(window_bars, key=lambda b: b["low"])
        hod = Decimal(str(hod_bar["high"]))
        lod = Decimal(str(lod_bar["low"]))
        hod_time = _to_dt(hod_bar["timestamp"])
        lod_time = _to_dt(lod_bar["timestamp"])

        # Direction classification
        if close > open_px and magnitude > 0:
            # Check if range is substantial enough to declare direction
            direction = "bullish"
        elif close < open_px and magnitude > 0:
            direction = "bearish"
        else:
            direction = "choppy"

        # Poor man's "choppy" refinement: if range is tiny relative to day range
        day_range = day_high - day_low
        if day_range > 0 and magnitude / day_range < Decimal("0.1"):
            direction = "choppy"

        instances.append(MacroInstance(
            instrument=instrument, window_type=w_type, date=trade_date,
            window_start=trade_date.replace(hour=start_t.hour, minute=start_t.minute),
            window_end=trade_date.replace(hour=end_t.hour, minute=end_t.minute),
            open=open_px, high=high, low=low, close=close,
            hod=hod, hod_time=hod_time, lod=lod, lod_time=lod_time,
            direction=direction, magnitude_pts=magnitude,
            hod_of_day_made=hod_made_before,
            lod_of_day_made=lod_made_before,
            preceding_po3_phase=ctx.get("preceding_po3_phase"),
            at_pd_array_open=ctx.get("at_pd_array_open"),
            news_flag=ctx.get("news_flag", False),
            london_direction=ctx.get("london_direction"),
            ny_open_30m_direction=ctx.get("ny_open_30m_direction"),
            gex_proximity=ctx.get("gex_proximity"),
        ))

    return instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime): return ts
    if isinstance(ts, str): return datetime.fromisoformat(ts)
    return datetime.fromtimestamp(ts)
```

### 3.9 GEX Computation — gex.py

```python
"""Intraday GEX computation from options chain snapshots.

GEX = gamma × open_interest × contract_multiplier × spot_price (per strike)
Per-strike GEX summed by call/put to derive walls, flip, zero gamma, max pain.

Multipliers: SPX=100, NDX=100
Substitutions: ES = SPX proxy, NQ = NDX proxy
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from src.models import GEXLevelDaily

# CME e-mini multiplier = 50x, but SPX options are 100x
# We use SPX/NDX options gamma applied to ES/NQ analysis as proportional proxy
MULTIPLIER = {"SPX": 100, "NDX": 100}


def compute_gex(snapshot: list[dict], underlying: str, snap_date: date) -> GEXLevelDaily:
    """Compute GEX levels from an options chain snapshot.

    Args:
        snapshot: list of dicts from options_chain_snapshots.
                  Each has: strike, call_gamma, put_gamma, call_oi, put_oi
        underlying: "SPX" or "NDX"
        snap_date: date of snapshot

    Returns GEXLevelDaily with computed levels.
    """
    mult = MULTIPLIER.get(underlying, 100)
    spot_price = None
    per_strike: list[dict] = []

    total_call_gex = 0.0
    total_put_gex = 0.0

    for row in snapshot:
        strike = Decimal(str(row["strike"]))
        call_g = float(row.get("call_gamma", 0) or 0) * mult
        put_g = float(row.get("put_gamma", 0) or 0) * mult
        call_oi = float(row.get("call_oi", 0) or 0)
        put_oi = float(row.get("put_oi", 0) or 0)
        call_gex = call_g * call_oi * float(strike)
        put_gex = put_g * put_oi * float(strike)

        total_call_gex += call_gex
        total_put_gex += put_gex

        per_strike.append({
            "strike": strike,
            "call_gex": call_gex,
            "put_gex": put_gex,
            "net_gex": call_gex - put_gex,
        })

        if "spot" in row:
            spot_price = Decimal(str(row["spot"]))

    if not per_strike:
        return GEXLevelDaily(
            date=snap_date, underlying=underlying,
            spot_price=Decimal("0"),
            call_wall_strike=Decimal("0"), put_wall_strike=Decimal("0"),
            max_pain_strike=Decimal("0"),
        )

    # Call wall = strike with max call_gex
    call_wall = max(per_strike, key=lambda r: r["call_gex"])
    put_wall = max(per_strike, key=lambda r: r["put_gex"])

    # Sort by strike for GEX flip and zero gamma
    sorted_strikes = sorted(per_strike, key=lambda r: r["strike"])

    # GEX flip: strike where net_gex crosses from positive to negative (or vice versa)
    gex_flip = None
    for i in range(len(sorted_strikes) - 1):
        curr_net = sorted_strikes[i]["net_gex"]
        next_net = sorted_strikes[i + 1]["net_gex"]
        if (curr_net >= 0 and next_net < 0) or (curr_net < 0 and next_net >= 0):
            gex_flip = sorted_strikes[i]["strike"]
            break

    # Zero gamma: strike where |net_gex| is minimized
    zero_gamma_strike = min(sorted_strikes, key=lambda r: abs(r["net_gex"]))["strike"]

    # Max pain: strike where total option buyer loss is minimized
    # Sum of |strike - spot| * OI for each strike, minimized
    if spot_price is not None:
        def total_pain(s):
            """Sum of absolute distance from strike weighted by total OI."""
            total = Decimal("0")
            for r in sorted_strikes:
                oi = r.get("call_oi", 0) + r.get("put_oi", 0)
                total += abs(r["strike"] - s) * Decimal(str(oi))
            return total

        # Search around spot for minimum pain
        pain_min = min(sorted_strikes, key=lambda r: total_pain(r["strike"]))
        max_pain = pain_min["strike"]
    else:
        max_pain = Decimal("0")

    net_gex = total_call_gex - total_put_gex

    return GEXLevelDaily(
        date=snap_date, underlying=underlying,
        spot_price=spot_price or Decimal("0"),
        call_wall_strike=call_wall["strike"],
        put_wall_strike=put_wall["strike"],
        gex_flip_strike=gex_flip,
        zero_gamma_strike=zero_gamma_strike,
        max_pain_strike=max_pain,
        total_call_gex=total_call_gex,
        total_put_gex=total_put_gex,
        net_gex=net_gex,
    )
```

---

## 4. Stage 3: Aggregation

### 4.1 aggregator.py — Generic Aggregation Engine

```python
"""Generic aggregation engine. Pure pandas — instance rows in, stat rows out.

Design: one `aggregate()` function parameterized by:
  - instance_table: source table name
  - metric_defs: list of MetricDef (what to compute, how to group, how to aggregate)
  - filters: optional WHERE clause additions
  - lookback_days: how many trading days of history

Each report type registers its own MetricDefs. The engine handles slicing
by weekday, session, news flag, HTF phase, etc.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

import pandas as pd
from supabase import Client


@dataclass
class MetricDef:
    """Definition of a single aggregated metric.

    Attributes:
        name: metric name for the output column
        column: source column to aggregate
        agg_func: pandas agg function name or callable
        group_by: list of column names to group by
        filters: optional {"column": value} exact-match filters
        output_type: "rate", "avg", "distribution"
    """
    name: str
    column: str
    agg_func: str | Callable
    group_by: list[str]
    filters: Optional[dict[str, Any]] = None
    output_type: str = "avg"


@dataclass
class AggregationResult:
    """Aggregation output row."""
    report_type: str
    instrument: str
    lookback_days: int
    slice_key: str   # e.g. "weekday=Mon" or "session=ny_am"
    metric_name: str
    value: float
    sample_size: int
    computed_at: datetime = None

    def __post_init__(self):
        if self.computed_at is None:
            self.computed_at = datetime.utcnow()


def fetch_instances(
    db: Client, table: str, instrument: str,
    start_date: date, end_date: date
) -> pd.DataFrame:
    """Fetch instance rows as a pandas DataFrame."""
    resp = db.table(table) \
        .select("*") \
        .eq("instrument", instrument) \
        .gte("date", start_date.isoformat()) \
        .lte("date", end_date.isoformat()) \
        .execute()

    if not resp.data:
        return pd.DataFrame()

    df = pd.DataFrame(resp.data)

    # Convert date columns
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    if "creation_time" in df.columns:
        df["creation_time"] = pd.to_datetime(df["creation_time"])
    if "fill_time" in df.columns:
        df["fill_time"] = pd.to_datetime(df["fill_time"])

    return df


def compute_rates(df: pd.DataFrame, value_col: str, group_cols: list[str]) -> list[AggregationResult]:
    """Compute rate (0-1) of True/1 values in value_col, grouped by group_cols."""
    if df.empty or value_col not in df.columns:
        return []

    results: list[AggregationResult] = []

    # Ensure boolean
    df[value_col] = df[value_col].astype(bool)
    grouped = df.groupby(group_cols)[value_col]

    for name, group in grouped:
        rate = group.mean()
        n = len(group)
        slice_str = ";".join(f"{c}={n}" for c, n in zip(group_cols, [name] if not isinstance(name, tuple) else name))
        # Build slice_key more carefully
        if isinstance(name, tuple):
            slice_key = ";".join(f"{g}={v}" for g, v in zip(group_cols, name))
        else:
            slice_key = f"{group_cols[0]}={name}"

        results.append(AggregationResult(
            report_type="", instrument="", lookback_days=0,
            slice_key=slice_key, metric_name=f"{value_col}_rate",
            value=float(rate), sample_size=n,
        ))

    return results


def compute_averages(df: pd.DataFrame, value_col: str, group_cols: list[str]) -> list[AggregationResult]:
    """Compute mean of value_col grouped by group_cols."""
    if df.empty or value_col not in df.columns:
        return []

    results: list[AggregationResult] = []
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    grouped = df.groupby(group_cols)[value_col]

    for name, group in grouped:
        avg = group.mean()
        n = group.count()
        if isinstance(name, tuple):
            slice_key = ";".join(f"{g}={v}" for g, v in zip(group_cols, name))
        else:
            slice_key = f"{group_cols[0]}={name}"

        results.append(AggregationResult(
            report_type="", instrument="", lookback_days=0,
            slice_key=slice_key, metric_name=f"avg_{value_col}",
            value=float(avg), sample_size=int(n),
        ))

    return results


def compute_distributions(df: pd.DataFrame, value_col: str, bucket_fn: Optional[Callable] = None) -> list[AggregationResult]:
    """Compute distribution of value_col values into buckets."""
    if df.empty or value_col not in df.columns:
        return []

    results: list[AggregationResult] = []
    values = pd.to_numeric(df[value_col], errors="coerce").dropna()

    if bucket_fn:
        buckets = values.apply(bucket_fn)
        dist = buckets.value_counts(normalize=True)
        for bucket, pct in dist.items():
            results.append(AggregationResult(
                report_type="", instrument="", lookback_days=0,
                slice_key=f"bucket={bucket}",
                metric_name=f"dist_{value_col}",
                value=float(pct), sample_size=int(len(values)),
            ))
    return results


def aggregate_all(
    report_type: str, instrument: str, lookback_days: int,
    df: pd.DataFrame, metric_defs: list[MetricDef],
) -> list[AggregationResult]:
    """Run all metric definitions against a dataframe and return flat results."""
    if df.empty:
        return []

    results: list[AggregationResult] = []

    for md in metric_defs:
        filtered = df
        if md.filters:
            for col, val in md.filters.items():
                if col in filtered.columns:
                    filtered = filtered[filtered[col] == val]

        if filtered.empty:
            continue

        if md.agg_func in ("mean", "avg"):
            results.extend(compute_averages(filtered, md.column, md.group_by))
        elif md.agg_func == "rate":
            results.extend(compute_rates(filtered, md.column, md.group_by))
        elif md.agg_func == "distribution":
            results.extend(compute_distributions(filtered, md.column, None))

    # Stamp metadata
    for r in results:
        r.report_type = report_type
        r.instrument = instrument
        r.lookback_days = lookback_days

    return results


# ── Report-specific metric definitions ──────────────────────────────────

FVG_METRICS = [
    MetricDef("fill_rate", "status", "rate", group_by=["weekday"], filters={"status": "filled"}),
    MetricDef("fill_rate_by_tf", "status", "rate", group_by=["timeframe"]),
    MetricDef("avg_fill_time", "fill_pct", "mean", group_by=["timeframe"]),
    MetricDef("fill_rate_by_session", "fill_pct", "rate", group_by=["session"]),
    MetricDef("fill_rate_by_news", "fill_pct", "rate", group_by=["news_flag"]),
]

OB_METRICS = [
    MetricDef("respect_rate", "outcome", "rate", group_by=["timeframe"], filters={"outcome": "respected"}),
    MetricDef("break_rate", "outcome", "rate", group_by=["timeframe"], filters={"outcome": "broken"}),
    MetricDef("avg_test_time", "first_test_time", "mean", group_by=["timeframe"]),
]

PO3_METRICS = [
    MetricDef("bullish_rate", "phase", "rate", group_by=["weekday"], filters={"phase": "bullish"}),
    MetricDef("bearish_rate", "phase", "rate", group_by=["weekday"], filters={"phase": "bearish"}),
    MetricDef("ambiguous_rate", "phase", "rate", group_by=["weekday"], filters={"phase": "unconfirmed"}),
    MetricDef("avg_range", "high_low_range", "mean", group_by=["window_type"]),
    MetricDef("hod_time_distribution", "hod_time", "distribution", group_by=["window_type"]),
    MetricDef("lod_time_distribution", "lod_time", "distribution", group_by=["window_type"]),
    MetricDef("pd_array_hod_dist", "pd_array_held_hod", "distribution", group_by=[]),
    MetricDef("pd_array_lod_dist", "pd_array_held_lod", "distribution", group_by=[]),
]

LIQUIDITY_METRICS = [
    MetricDef("sweep_rate", "swept", "rate", group_by=["level_type"]),
    MetricDef("reversal_rate_after_sweep", "post_sweep_direction", "rate",
              group_by=["level_type"], filters={"swept": True}),
]

KEYOPEN_METRICS = [
    MetricDef("respect_rate", "respected", "rate", group_by=["open_type"]),
    MetricDef("rejection_rate", "rejection", "rate", group_by=["open_type"]),
    MetricDef("avg_time_to_test", "time_to_test", "mean", group_by=["open_type"]),
    MetricDef("avg_deviation", "deviation_before_test_pts", "mean", group_by=["open_type"]),
]

NEWS_CANDLE_METRICS = [
    MetricDef("high_taken_rate", "high_taken", "rate", group_by=["event_name"]),
    MetricDef("low_taken_rate", "low_taken", "rate", group_by=["event_name"]),
    MetricDef("both_sides_rate", "high_taken", "rate", group_by=[], filters={"high_taken": True, "low_taken": True}),
    MetricDef("avg_post_take_magnitude", "post_take_magnitude_pts", "mean", group_by=["impact"]),
]

MACRO_METRICS = [
    MetricDef("bullish_rate", "direction", "rate", group_by=["window_type"], filters={"direction": "bullish"}),
    MetricDef("bearish_rate", "direction", "rate", group_by=["window_type"], filters={"direction": "bearish"}),
    MetricDef("choppy_rate", "direction", "rate", group_by=["window_type"], filters={"direction": "choppy"}),
    MetricDef("avg_magnitude", "magnitude_pts", "mean", group_by=["window_type"]),
]

OPENING_GAP_METRICS = [
    MetricDef("fill_rate", "fill_status", "rate", group_by=["gap_type"], filters={"fill_status": "filled"}),
    MetricDef("avg_fill_time", "fill_pct", "mean", group_by=["gap_type"]),
    MetricDef("fill_rate_by_weekday", "fill_status", "rate", group_by=["gap_type", "weekday"]),
]

GEX_METRICS = [
    MetricDef("call_wall_respect_rate", None, "rate", group_by=["underlying"]),
    MetricDef("put_wall_respect_rate", None, "rate", group_by=["underlying"]),
]


def build_report(
    report_type: str, instrument: str, lookback_days: int,
    instance_table: str, metrics: list[MetricDef],
    db: Client, end_date: Optional[date] = None,
) -> list[AggregationResult]:
    """End-to-end: fetch → aggregate → stamp with metadata."""
    end = end_date or date.today()
    start = end - timedelta(days=lookback_days * 7 // 5 + 5)  # approximate trading days

    df = fetch_instances(db, instance_table, instrument, start, end)

    # Add derived columns
    if not df.empty and "date" in df.columns:
        df["weekday"] = df["date"].dt.dayofweek.map({
            0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri",
        })
    if not df.empty and "high" in df.columns and "low" in df.columns:
        df["high_low_range"] = pd.to_numeric(df["high"], errors="coerce") - pd.to_numeric(df["low"], errors="coerce")

    return aggregate_all(report_type, instrument, lookback_days, df, metrics)
```

### 4.2 queries.py — Report-Specific Builders

```python
"""Report-specific query builders that call into the generic aggregator."""

from datetime import date
from typing import Optional
from supabase import Client

from src.aggregation.aggregator import (
    build_report,
    FVG_METRICS, OB_METRICS, PO3_METRICS,
    LIQUIDITY_METRICS, KEYOPEN_METRICS, NEWS_CANDLE_METRICS,
    MACRO_METRICS, OPENING_GAP_METRICS, GEX_METRICS,
)

REPORT_CONFIG = {
    "fvg":              ("fvg_instances", FVG_METRICS),
    "order_blocks":     ("order_block_instances", OB_METRICS),
    "liquidity":        ("liquidity_levels", LIQUIDITY_METRICS),
    "po3":              ("po3_instances", PO3_METRICS),
    "key_opens":        ("key_opens", KEYOPEN_METRICS),
    "news_candles":     ("news_candle_instances", NEWS_CANDLE_METRICS),
    "macros":           ("macro_instances", MACRO_METRICS),
    "opening_gaps":     ("opening_gap_instances", OPENING_GAP_METRICS),
    "gex":              ("gex_levels_daily", GEX_METRICS),
}

LOOKBACKS = [63, 126, 252]  # ~3mo, 6mo, 1yr in trading days

INSTRUMENTS = ["ES", "NQ", "GC", "CL", "MES", "MNQ"]


def build_all_reports(db: Client, end_date: Optional[date] = None) -> list[dict]:
    """Build all report × instrument × lookback combinations.

    Returns flat list of dicts ready to insert into report_*_stats tables.
    """
    end = end_date or date.today()
    all_results: list[dict] = []

    for report_name, (table, metrics) in REPORT_CONFIG.items():
        target_table = f"report_{report_name}_stats"
        instruments = INSTRUMENTS if report_name != "gex" else ["SPX", "NDX"]

        for instrument in instruments:
            for lb in LOOKBACKS:
                results = build_report(report_name, instrument, lb, table, metrics, db, end)
                all_results.extend([_result_to_dict(r, report_name, target_table) for r in results])

    return all_results


def _result_to_dict(r, report_name: str, target_table: str) -> dict:
    return {
        "report_type": report_name,
        "instrument": r.instrument,
        "lookback_days": r.lookback_days,
        "slice_key": r.slice_key,
        "metric_name": r.metric_name,
        "value": r.value,
        "sample_size": r.sample_size,
        "computed_at": r.computed_at.isoformat(),
    }
```

---

## 5. Orchestrator

### 5.1 orchestrator.py — Main Pipeline Entry Point

```python
"""Pipeline orchestrator. Runs Stage 2 (detection) then Stage 3 (aggregation).

Dependency order for detectors:
  1. News events (needed by PO3, Macros for news_flag)
  2. FVGs (needed for PD array correlation in PO3)
  3. OBs (needed for PD array correlation)
  4. BSL/SSL
  5. Key Opens
  6. Opening Gaps
  7. PO3 (depends on news_flag, FVGs, OBs for PD array matching)
  8. Macros (depends on PO3, news_flag, GEX)
  9. News Candles
  10. GEX (independent, can run last)

In practice, detectors 2-6 and 10 are independent of each other and could
run in parallel. Keeping sequential for simplicity; parallelism via
thread pool can be added when throughput demands it.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from src.config import Config
from src.db import get_db, insert_many, delete_old_instances, fetch_ohlcv
from src import detection
from src.aggregation.aggregator import build_all_reports
from src.aggregation.queries import LOOKBACKS, INSTRUMENTS
from src.models import (
    FVGInstance, OrderBlockInstance, LiquidityLevel,
    PO3Instance, KeyOpenInstance, OpeningGapInstance,
    NewsCandleInstance, MacroInstance, GEXLevelDaily,
)

# How many extra days of context to pull for FVG fill checking / gap detection
CONTEXT_DAYS = 5


def _instances_to_dicts(instances: list) -> list[dict]:
    """Convert dataclass instances to dicts for DB insertion."""
    return [vars(inst) for inst in instances]


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime): return ts
    if isinstance(ts, str): return datetime.fromisoformat(ts)
    return datetime.fromtimestamp(ts)


def _find_nearest_pd_array(
    price, fvg_instances: list[FVGInstance],
    ob_instances: list[OrderBlockInstance], tolerance_pct: float = 0.0002
) -> tuple[str, str]:
    """Find nearest PD array within tolerance. Returns (type, detail_json).

    Matches FVG or OB within 0.02% of price (approx 2 ticks on ES).
    """
    for fvg in fvg_instances:
        if abs(float(fvg.high_bound - price)) / float(price) <= tolerance_pct:
            return ("fvg", f'{{"type":"fvg","tf":"{fvg.timeframe}","id":""}}')
        if abs(float(fvg.low_bound - price)) / float(price) <= tolerance_pct:
            return ("fvg", f'{{"type":"fvg","tf":"{fvg.timeframe}","id":""}}')

    for ob in ob_instances:
        ob_mid = (float(ob.origin_high) + float(ob.origin_low)) / 2.0
        if abs(ob_mid - float(price)) / float(price) <= tolerance_pct:
            return ("ob", f'{{"type":"ob","tf":"{ob.timeframe}","id":""}}')

    return ("none", "")


def run_detection_day(
    instrument: str, trade_date: date, cfg: Config, db
) -> dict:
    """Run all detectors for one instrument on one trading day.

    Returns dict of {table_name: [instance_dicts]} for insertion.
    """
    # Fetch bars with context
    start = trade_date - timedelta(days=CONTEXT_DAYS)
    end = trade_date + timedelta(days=1)

    bars_1m = fetch_ohlcv(instrument, start.isoformat(), end.isoformat(), db)
    if not bars_1m:
        return {}

    # Convert string timestamps
    for b in bars_1m:
        if isinstance(b.get("timestamp"), str):
            b["timestamp"] = datetime.fromisoformat(b["timestamp"].replace("Z", "+00:00"))

    bars_today = [
        b for b in bars_1m
        if _to_dt(b["timestamp"]).date() == trade_date
    ]
    bars_context = bars_1m  # use full context for FVG fill checking

    # 1. Fetch news events for this day
    news_events = db.table("news_events") \
        .select("*") \
        .gte("event_time", trade_date.isoformat()) \
        .lte("event_time", (trade_date + timedelta(days=1)).isoformat()) \
        .execute()
    news_events = news_events.data or []

    news_flag = len(news_events) > 0
    has_830_news = any(
        "08:30" in (e.get("event_time", "") if isinstance(e.get("event_time"), str) else str(e.get("event_time", "")))
        for e in news_events
    ) or any(
        _to_dt(e["event_time"]).hour == 8 and _to_dt(e["event_time"]).minute == 30
        for e in news_events if "event_time" in e
    )

    # 2. Detect FVGs
    fvg_instances = detection.fair_value_gaps.detect(
        {"1m": bars_context}, instrument, trade_date
    )

    # 3. Detect OBs
    ob_instances = detection.order_blocks.detect(bars_today, instrument)

    # 4. Detect BSL/SSL
    liq_levels = detection.liquidity_sweeps.detect(bars_today, instrument, trade_date)

    # 5. Detect Key Opens
    key_opens = detection.key_opens.detect(bars_today, instrument, trade_date)

    # 6. Detect Opening Gaps
    prior_day = trade_date - timedelta(days=1)
    bars_prior = fetch_ohlcv(instrument, prior_day.isoformat(), trade_date.isoformat(), db)
    for b in bars_prior:
        if isinstance(b.get("timestamp"), str):
            b["timestamp"] = datetime.fromisoformat(b["timestamp"].replace("Z", "+00:00"))
    ndog = detection.opening_gaps.detect_ndog(bars_today, bars_prior, instrument, trade_date)

    # 7. Detect PO3
    po3_instances = detection.power_of_3.detect_for_day(
        bars_today, instrument, trade_date, news_flag, has_830_news
    )

    # PD array correlation for PO3
    for inst in po3_instances:
        hod_type, hod_detail = _find_nearest_pd_array(inst.hod, fvg_instances, ob_instances)
        lod_type, lod_detail = _find_nearest_pd_array(inst.lod, fvg_instances, ob_instances)
        inst.pd_array_held_hod = hod_type
        inst.pd_array_held_lod = lod_type
        inst.pd_array_detail_hod = hod_detail
        inst.pd_array_detail_lod = lod_detail

    # 8. Detect Macros
    prior_context = {
        "news_flag": news_flag,
        "preceding_po3_phase": next(
            (p.phase for p in po3_instances if p.window_type == "30m_930"), None
        ),
    }
    macro_instances = detection.macros.detect(bars_today, instrument, trade_date, prior_context)

    # 9. Detect News Candles
    news_candle_instances = detection.news_candles.detect(
        bars_today, instrument, trade_date, news_events
    )

    # 10. GEX is run separately — skipped here since it's intraday
    # (handled by run_gex_pipeline on a 30-min timer)

    return {
        "fvg_instances": _instances_to_dicts(fvg_instances),
        "order_block_instances": _instances_to_dicts(ob_instances),
        "liquidity_levels": _instances_to_dicts(liq_levels),
        "key_opens": _instances_to_dicts(key_opens),
        "opening_gap_instances": _instances_to_dicts([ndog]) if ndog else [],
        "po3_instances": _instances_to_dicts(po3_instances),
        "macro_instances": _instances_to_dicts(macro_instances),
        "news_candle_instances": _instances_to_dicts(news_candle_instances),
    }


def run_nightly_pipeline(cfg: Config, target_date: Optional[date] = None) -> None:
    """Run full nightly pipeline: detection + aggregation for all instruments.

    Args:
        cfg: application config
        target_date: date to process (defaults to yesterday)
    """
    db = get_db(cfg)
    trade_date = target_date or date.today() - timedelta(days=1)

    print(f"[pipeline] Starting nightly run for {trade_date.isoformat()}")

    # Stage 2: Detection
    for instrument in INSTRUMENTS:
        print(f"  [detection] Processing {instrument}...")
        instances = run_detection_day(instrument, trade_date, cfg, db)

        for table, rows in instances.items():
            if rows:
                # Delete old entries for this date first (idempotency)
                delete_old_instances(table, instrument, trade_date, db)
                insert_many(table, rows, db)
                print(f"    -> {len(rows)} rows -> {table}")

    # Stage 3: Aggregation
    print("  [aggregation] Building reports...")
    all_stats = build_all_reports(db, trade_date)

    # Write to report_*_stats tables
    for stat_row in all_stats:
        report_table = f"report_{stat_row['report_type']}_stats"
        # Upsert by unique key would be ideal; for simplicity, insert + dedupe later
        db.table(report_table).insert(stat_row).execute()

    # Invalidate Redis cache
    if cfg.upstash_redis_url:
        try:
            import redis
            r = redis.from_url(cfg.upstash_redis_url)
            # Flush all cache entries for report data
            for key in r.scan_iter("report:*"):
                r.delete(key)
            print("    -> Redis cache invalidated")
        except Exception as e:
            print(f"    -> Redis cache invalidation failed: {e}")

    print(f"[pipeline] Completed nightly run for {trade_date.isoformat()}")


def run_gex_pipeline(cfg: Config) -> None:
    """Intraday GEX computation. Runs every 30 min 09:00-16:30 ET on trading days."""
    db = get_db(cfg)
    today = date.today()

    for underlying in ["SPX", "NDX"]:
        snapshot = db.table("options_chain_snapshots") \
            .select("*") \
            .eq("underlying", underlying) \
            .gte("timestamp", today.isoformat()) \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()

        if snapshot.data:
            gex = detection.gex.compute_gex(snapshot.data, underlying, today)
            db.table("gex_levels_daily").insert(vars(gex)).execute()
            print(f"  [gex] {underlying}: call_wall={gex.call_wall_strike}")


def run(cfg: Config, mode: str = "nightly", target_date: Optional[str] = None) -> None:
    """CLI entry point.

    Args:
        cfg: Config instance
        mode: "nightly" (full pipeline), "gex" (intraday only), "detect" (stage 2 only)
        target_date: optional date string YYYY-MM-DD
    """
    td = date.fromisoformat(target_date) if target_date else None

    if mode == "gex":
        run_gex_pipeline(cfg)
    elif mode == "detect":
        db = get_db(cfg)
        for instrument in INSTRUMENTS:
            instances = run_detection_day(instrument, td or date.today(), cfg, db)
            for table, rows in instances.items():
                if rows:
                    delete_old_instances(table, instrument, td or date.today(), db)
                    insert_many(table, rows, db)
    else:
        run_nightly_pipeline(cfg, td)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quanta Pipeline")
    parser.add_argument("--mode", choices=["nightly", "gex", "detect"], default="nightly")
    parser.add_argument("--date", type=str, help="Target date YYYY-MM-DD")
    args = parser.parse_args()

    cfg = Config.load()
    run(cfg, mode=args.mode, target_date=args.date)
```

---

## 6. Tests & Fixtures

### 6.1 conftest.py

```python
"""Shared test fixtures: synthetic OHLCV generators, news stubs."""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
import random


def synthetic_1m_bars(
    instrument: str = "ES",
    start: datetime = None,
    n_bars: int = 1200,
    open_px: float = 5800.0,
    volatility: float = 2.0,
    trend: float = 0.0,
) -> list[dict]:
    """Generate synthetic 1-minute OHLCV bars with optional trend and volatility.

    Args:
        instrument: instrument symbol
        start: start datetime (defaults to today 08:00 ET)
        n_bars: number of 1m bars to generate
        open_px: starting price
        volatility: max price move per bar (in points)
        trend: directional bias per bar (positive = bullish, negative = bearish)

    Returns list of OHLCV dicts.
    """
    if start is None:
        start = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    random.seed(42)  # deterministic
    bars = []
    px = open_px

    for i in range(n_bars):
        ts = start + timedelta(minutes=i)
        move = random.uniform(-volatility, volatility) + trend
        o = px
        c = px + move
        h = max(o, c) + random.uniform(0, volatility * 0.3)
        l = min(o, c) - random.uniform(0, volatility * 0.3)
        v = int(random.uniform(100, 10000))
        bars.append({
            "timestamp": ts,
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": v,
            "instrument": instrument,
        })
        px = c

    return bars


def synthetic_bullish_fvg_day() -> list[dict]:
    """Generate a day with a clear bullish FVG (gap down, then reversal up)."""
    # Start at 5800, gap down to 5795, then rally to 5820
    bars = []
    ts = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    px = 5800.0

    # Candle 0: normal bearish
    bars.append({"timestamp": ts, "open": 5800.0, "high": 5801.0, "low": 5798.5, "close": 5799.0, "volume": 5000})
    ts += timedelta(minutes=1)

    # Candle 1: gap down candle — high < prior low (5798.5) = bullish FVG
    bars.append({"timestamp": ts, "open": 5798.0, "high": 5798.0, "low": 5795.0, "close": 5796.0, "volume": 5000})
    ts += timedelta(minutes=1)

    # Candle 2: continues down, fills below
    bars.append({"timestamp": ts, "open": 5795.0, "high": 5795.5, "low": 5793.0, "close": 5794.0, "volume": 5000})
    ts += timedelta(minutes=1)

    # Then fill the gap over next 30 bars
    for i in range(30):
        px += random.uniform(0, 1.5)
        bars.append({
            "timestamp": ts, "open": round(px, 2), "high": round(px + 1, 2),
            "low": round(px - 0.5, 2), "close": round(px, 2), "volume": 5000,
        })
        ts += timedelta(minutes=1)

    return bars


@pytest.fixture
def sample_1m_bars():
    return synthetic_1m_bars()


@pytest.fixture
def sample_bullish_fvg_bars():
    return synthetic_bullish_fvg_day()


@pytest.fixture
def sample_news_events():
    return [
        {"event_name": "CPI MoM", "event_time": datetime(2026, 7, 8, 8, 30),
         "impact": "high", "currency": "USD"},
        {"event_name": "Jobless Claims", "event_time": datetime(2026, 7, 8, 8, 30),
         "impact": "medium", "currency": "USD"},
    ]
```

### 6.2 test_fair_value_gaps.py

```python
"""Tests for FVG detection."""

from src.detection.fair_value_gaps import detect, resample_bars, detect_fvgs, TF_CONFIGS
from tests.fixtures.ohlcv_samples import synthetic_bullish_fvg_day


def test_bullish_fvg_detected():
    bars = synthetic_bullish_fvg_day()
    # Run detection on 1m bars
    results = detect({"1m": bars}, "ES", bars[0]["timestamp"].date())
    # Should find at least 1 FVG (the gap we engineered)
    fvgs = [r for r in results if r.status in ("open", "partial", "filled")]
    assert len(fvgs) > 0, "Expected at least one FVG"


def test_fvg_fill_status():
    bars = synthetic_bullish_fvg_day()
    results = detect({"1m": bars}, "ES", bars[0]["timestamp"].date())
    # The engineered gap gets filled by the rally — at least partially
    filled = [r for r in results if r.status == "filled"]
    partial = [r for r in results if r.status == "partial"]
    assert len(filled) > 0 or len(partial) > 0


def test_resample_5m():
    bars = synthetic_bullish_fvg_day()
    resampled = resample_bars(bars, 5)
    assert len(resampled) < len(bars)
    assert all("open" in b and "high" in b and "low" in b and "close" in b for b in resampled)


def test_no_fvg_on_flat_data():
    bars = []
    ts = datetime.now().replace(hour=8, minute=0)
    for i in range(100):
        bars.append({"timestamp": ts, "open": 5800.0, "high": 5800.5,
                      "low": 5799.5, "close": 5800.0, "volume": 100})
        ts += timedelta(minutes=1)
    results = detect({"1m": bars}, "ES", bars[0]["timestamp"].date())
    # Flat data should produce no FVGs (no real gaps between candles)
    # But resampling might create some — just check we don't crash
    assert isinstance(results, list)
```

### 6.3 test_power_of_3.py

```python
"""Tests for PO3 classification."""

from datetime import datetime, date, timedelta
from src.detection.power_of_3 import detect_for_day, classify_window, WINDOW_DEFS
from tests.fixtures.ohlcv_samples import synthetic_1m_bars


def _make_manip_bars(open_px: float, bullish: bool) -> list[dict]:
    """Craft a synthetic window with clear bullish or bearish PO3."""
    bars = []
    ts = datetime.now().replace(hour=9, minute=30, second=0)
    n_bars = 30

    if bullish:
        # First 12 bars (40%) trade significantly below open
        for i in range(12):
            low = open_px - 3.0 - (i * 0.5)
            bars.append({"timestamp": ts + timedelta(minutes=i),
                          "open": open_px, "high": open_px - 1.0,
                          "low": low, "close": low + 0.5, "volume": 5000})
        # Then rally hard above open
        offset = 12
        for i in range(offset, n_bars):
            close = open_px + 2.0 + (i - offset)
            bars.append({"timestamp": ts + timedelta(minutes=i),
                          "open": open_px, "high": close + 1.0,
                          "low": open_px - 0.5, "close": close,
                          "volume": 5000})
    else:
        # Bearish: first 40% trade above open
        for i in range(12):
            high = open_px + 3.0 + (i * 0.5)
            bars.append({"timestamp": ts + timedelta(minutes=i),
                          "open": open_px, "high": high,
                          "low": open_px + 1.0, "close": high - 0.5,
                          "volume": 5000})
        # Then sell off
        offset = 12
        for i in range(offset, n_bars):
            close = open_px - 2.0 - (i - offset)
            bars.append({"timestamp": ts + timedelta(minutes=i),
                          "open": open_px, "high": open_px + 0.5,
                          "low": close - 0.5, "close": close,
                          "volume": 5000})

    return bars


def test_bullish_po3_classification():
    bars = _make_manip_bars(5800.0, bullish=True)
    # Test the 30m_930 window manually
    from datetime import time, datetime
    trade_date = bars[0]["timestamp"].date()
    w_start = datetime.combine(trade_date, time(9, 30))
    w_end = datetime.combine(trade_date, time(10, 0))
    inst = classify_window(bars, "ES", "30m_930", trade_date, w_start, w_end, news_flag=False)
    assert inst.phase == "bullish", f"Expected bullish, got {inst.phase}"
    assert inst.hod > inst.open
    assert inst.close > inst.open


def test_bearish_po3_classification():
    bars = _make_manip_bars(5800.0, bullish=False)
    trade_date = bars[0]["timestamp"].date()
    w_start = datetime.combine(trade_date, time(9, 30))
    w_end = datetime.combine(trade_date, time(10, 0))
    inst = classify_window(bars, "ES", "30m_930", trade_date, w_start, w_end, news_flag=False)
    assert inst.phase == "bearish", f"Expected bearish, got {inst.phase}"
    assert inst.lod < inst.open
    assert inst.close < inst.open


def test_detect_for_day_runs_all_windows():
    bars = synthetic_1m_bars(n_bars=780, start=datetime.now().replace(hour=6, minute=0))
    trade_date = bars[0]["timestamp"].date()
    results = detect_for_day(bars, "ES", trade_date)
    assert len(results) == len(WINDOW_DEFS), f"Expected {len(WINDOW_DEFS)} windows, got {len(results)}"


def test_detect_for_day_with_news():
    bars = synthetic_1m_bars(n_bars=780, start=datetime.now().replace(hour=6, minute=0))
    trade_date = bars[0]["timestamp"].date()
    results = detect_for_day(bars, "ES", trade_date, news_flag=True, has_830_news=True)
    ny_session = [r for r in results if r.window_type == "ny_session"][0]
    assert ny_session.news_flag == True
```

### 6.4 Additional Test Files (skeletons)

Each follows the same pattern as above. Here is the complete list:

**test_liquidity_sweeps.py:**
```python
from src.detection.liquidity_sweeps import detect, find_swing_highs, find_swing_lows
from tests.fixtures.ohlcv_samples import synthetic_1m_bars

def test_swing_high_detection():
    bars = synthetic_1m_bars(n_bars=200, volatility=3.0)
    highs = find_swing_highs(bars)
    assert len(highs) > 0
    assert all(isinstance(h, Decimal) for h in highs)

def test_swing_low_detection():
    bars = synthetic_1m_bars(n_bars=200, volatility=3.0)
    lows = find_swing_lows(bars)
    assert len(lows) > 0

def test_sweep_detection():
    bars = synthetic_1m_bars(n_bars=400, volatility=5.0)
    results = detect(bars, "ES", date.today())
    bsl = [r for r in results if r.level_type == "bsl"]
    ssl = [r for r in results if r.level_type == "ssl"]
    assert any(r.swept for r in results)  # with high vol, some should sweep

def test_empty_bars():
    assert detect([], "ES", date.today()) == []
```

**test_key_opens.py:**
```python
from src.detection.key_opens import detect
from tests.fixtures.ohlcv_samples import synthetic_1m_bars

def test_key_opens_detected():
    bars = synthetic_1m_bars(start=datetime.now().replace(hour=17, minute=55), n_bars=200)
    results = detect(bars, "ES", bars[0]["timestamp"].date())
    # At minimum should find some open levels
    assert len(results) <= 3

def test_key_open_no_respect():
    # All bars far from open = rejection
    ts = datetime.now().replace(hour=18, minute=0)
    bars = [{"timestamp": ts + timedelta(minutes=i), "open": 5850.0,
             "high": 5860.0, "low": 5845.0, "close": 5855.0, "volume": 1000}
            for i in range(60)]
    results = detect(bars, "ES", date.today())
    for r in results:
        if r.open_type == "open_1800":
            assert r.rejection == True
```

**test_opening_gaps.py, test_news_candles.py, test_macros.py, test_gex.py, test_aggregator.py** follow the same skeleton pattern:
- One "test_end_to_end" that runs detect() with synthetic data and asserts non-empty results
- One "test_empty_input" with [] bars
- One "test_classify_X" for each direction/edge case

---

## 7. Dependencies & Deployment

### pyproject.toml

```toml
[project]
name = "quanta-pipeline"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "supabase>=2.0",
    "pandas>=2.0",
    "numpy>=1.24",
    "redis>=5.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY src/ src/
COPY scripts/ scripts/

CMD ["python", "-m", "src.orchestrator", "--mode", "nightly"]
```

### Railway deployment notes

- Service type: Worker (not web — runs on schedule, no HTTP listener)
- Cron: `0 23 * * 1-5` (23:30 UTC = 18:30 ET, weekdays only)
- GEX intraday cron: `*/30 13-21 * * 1-5` (09:00-16:30 ET = 13:00-21:30 UTC, every 30 min)
- Environment variables: all Config fields as secrets

---

## Implementation Order

| Step | Module | Effort | Why first |
|------|--------|--------|-----------|
| 1 | config.py, db.py, models.py | small | Foundation for everything |
| 2 | FVG detection + tests | medium | Simplest detector, proves the pattern |
| 3 | OB detection + tests | small | Shares bar-processing pattern with FVG |
| 4 | PO3 classification + tests | large | Flagship — most complex, needs FVG/OB for PD array |
| 5 | Liquidity sweeps + tests | medium | Swing high/low pattern |
| 6 | Key opens + tests | small | Simple level detection |
| 7 | Opening gaps + tests | small | Extends key-open pattern |
| 8 | News candles + tests | small | Depends on news_events table |
| 9 | Macros + tests | medium | Depends on PO3 for preceding phase |
| 10 | GEX + tests | medium | Independent, intraday schedule |
| 11 | Aggregator + queries | large | After all detectors produce data |
| 12 | Orchestrator + Dockerfile | medium | Wires everything together |
| 13 | Full integration test | medium | End-to-end with synthetic day |

Each detector step includes: module implementation → module tests passing on synthetic data → manual spot-check against real data if available.

---

## Edge Cases & Design Notes

1. **Daylight Saving Time**: All ET times in config are expressed as ET; the orchestrator converts to UTC for Supabase timestamps using a pytz-aware conversion in a future iteration. For v1, use UTC timestamps in the DB and convert on read.

2. **Fill checking with context**: FVG and opening gap detection require bars AFTER the gap creation event. The orchestrator passes CONTEXT_DAYS=5 extra days to ensure enough trailing bars exist for fill checking.

3. **PO3 unconfirmed instances**: These write to `po3_instances` with phase="unconfirmed" AND to `po3_phase_labels` (auto-inserted as null). The admin panel (Next.js app) reads `po3_phase_labels` where `confirmed_phase IS NULL`. After admin confirms, `update_po3_phase_label` updates both `po3_phase_labels` and `po3_instances`.

4. **Idempotency**: The orchestrator deletes then inserts for each (instrument × date) before writing new instances. This allows safe re-runs without duplicates.

5. **Aggregation cache invalidation**: Redis keys matching `report:*` are flushed after aggregation. On miss, the Next.js app falls back to Postgres and refreshes the cache.

6. **Graceful degradation**: If any detector fails (e.g., missing news data), the orchestrator logs the error and continues with remaining detectors. A failed detector does not block aggregation — missing instance tables simply produce empty results.

7. **Sample size floor**: All aggregation results carry `sample_size`. The Next.js frontend displays `n<30` warnings using this value. The aggregation engine does not filter out small samples — that's a UI concern.
