"""Reusable bar resampler: aggregate 1m OHLCV bars into higher timeframes.

Pure function, no DB or I/O. Works with any list of OHLCV dicts sorted
ascending by timestamp. Used by FVG, OB, and any detector that needs
multi-timeframe analysis.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

log = logging.getLogger(__name__)


def validate_bar(bar: dict[str, Any]) -> bool:
    """Check that a bar dict has all required OHLCV keys with non-None numeric values."""
    required = {"timestamp", "open", "high", "low", "close"}
    if not all(k in bar for k in required):
        return False
    for k in ("open", "high", "low", "close"):
        if bar.get(k) is None:
            return False
    return True


def resample_bars(bars: list[dict[str, Any]], timeframe_minutes: int) -> list[dict[str, Any]]:
    """Aggregate 1m bars into higher timeframe OHLC.

    Pure function. Input bars must be sorted ascending by timestamp.
    Returns list of dicts with keys: timestamp, open, high, low, close.
    """
    if not bars:
        return []

    result: list[dict[str, Any]] = []
    period: list[dict[str, Any]] = []

    for bar in bars:
        if not validate_bar(bar):
            log.warning("Skipping invalid bar: %s", bar.get("timestamp", "unknown"))
            continue
        bar_dt = _to_dt(bar["timestamp"])

        if period and (
            bar_dt.timestamp() - _to_dt(period[0]["timestamp"]).timestamp()
            >= timeframe_minutes * 60
        ):
            result.append(_collapse_period(period))
            period = []

        period.append(bar)

    if period:
        result.append(_collapse_period(period))

    return result


def _collapse_period(bars: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse a list of 1m bars into one OHLC bar."""
    return {
        "timestamp": bars[0]["timestamp"],
        "open": Decimal(str(bars[0]["open"])),
        "high": max(Decimal(str(b["high"])) for b in bars),
        "low": min(Decimal(str(b["low"])) for b in bars),
        "close": Decimal(str(bars[-1]["close"])),
    }


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromtimestamp(ts)
