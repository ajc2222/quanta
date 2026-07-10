"""Fair Value Gap detection across multiple timeframes.

A bullish FVG forms when the middle candle's high < the prior candle's low,
leaving a gap between prior low and middle high. Bearish is the mirror.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from src.detection.models import FVGInstance
from src.detection.resample import resample_bars


TF_CONFIGS: list[tuple[str, int]] = [
    ("1m", 1), ("5m", 5), ("15m", 15), ("1H", 60), ("4H", 240), ("1D", 1440),
]


def detect_fvgs(bars: list[dict], instrument: str, timeframe: str, tf_minutes: int) -> list[FVGInstance]:
    """Detect FVGs in bars of a given timeframe.

    For a 3-candle sequence (c0, c1, c2):
      Bullish FVG: c1.high < c0.low  ->  gap [c1.high, c0.low]
      Bearish FVG: c1.low > c0.high  ->  gap [c0.high, c1.low]

    Checks subsequent bars to determine if the gap was filled.
    """
    tf_bars = resample_bars(bars, tf_minutes) if tf_minutes > 1 else [
        {
            "timestamp": _to_dt(b["timestamp"]),
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

        if c1["high"] < c0["low"]:
            gap_low = c1["high"]
            gap_high = c0["low"]
            is_bullish = True
        elif c1["low"] > c0["high"]:
            gap_low = c0["high"]
            gap_high = c1["low"]

        if gap_low is not None and gap_high is not None:
            creation_time = c1["timestamp"]
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
    if start_idx >= len(bars):
        return None, None, "open"

    total_range = float(gap_high - gap_low)
    if total_range <= 0:
        return 100.0, bars[start_idx]["timestamp"], "filled"

    max_penetration = Decimal("0")
    fill_time = None

    for j in range(start_idx, len(bars)):
        bar = bars[j]

        if bar["low"] <= gap_high and bar["high"] >= gap_low:
            penetration = min(bar["high"], gap_high) - max(bar["low"], gap_low)
            pct = float(penetration) / total_range * 100
            if pct > max_penetration:
                max_penetration = pct
                fill_time = bar["timestamp"]

            if bar["low"] <= gap_low and bar["high"] >= gap_high:
                return 100.0, bar["timestamp"], "filled"

    if max_penetration > 0:
        return min(float(max_penetration), 99.9), fill_time, "partial"

    return None, None, "open"


def detect(bars: dict[str, list[dict]], instrument: str, date: date) -> list[FVGInstance]:
    """Detect FVGs across all timeframes for a given day's bars.

    Args:
        bars: dict keyed by timeframe string.
              Pass the same 1m source; each TF handles resampling internally.
        instrument: e.g. "ES"
        date: trading date

    Returns flat list of all FVGInstances detected.
    """
    raw_1m = bars.get("1m", [])
    all_instances: list[FVGInstance] = []

    for tf_name, tf_minutes in TF_CONFIGS:
        tf_instances = detect_fvgs(raw_1m, instrument, tf_name, tf_minutes)
        all_instances.extend(tf_instances)

    return all_instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromtimestamp(ts)
