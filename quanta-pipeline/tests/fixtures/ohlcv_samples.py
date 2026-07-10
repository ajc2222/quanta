"""Synthetic OHLCV generators for tests. Deterministic (seed=42)."""

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
    """Generate synthetic 1-minute OHLCV bars with optional trend and volatility."""
    if start is None:
        start = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    random.seed(42)
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
    """Generate a day with a clear bullish FVG (gap down, then reversal up).

    Deterministic — uses random.seed(42). The rally pushes above the gap
    and then pulls back through it, ensuring fill detection.
    """
    random.seed(42)
    bars = []
    ts = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    px = 5800.0

    bars.append({"timestamp": ts, "open": 5800.0, "high": 5801.0, "low": 5798.5, "close": 5799.0, "volume": 5000})
    ts += timedelta(minutes=1)
    bars.append({"timestamp": ts, "open": 5798.0, "high": 5798.0, "low": 5795.0, "close": 5796.0, "volume": 5000})
    ts += timedelta(minutes=1)
    bars.append({"timestamp": ts, "open": 5795.0, "high": 5795.5, "low": 5793.0, "close": 5794.0, "volume": 5000})
    ts += timedelta(minutes=1)

    # Rally up above the gap, then pull back through it
    for i in range(15):
        px += random.uniform(0.3, 1.5)
        bars.append({
            "timestamp": ts, "open": round(px, 2), "high": round(px + 1, 2),
            "low": round(px - 0.5, 2), "close": round(px, 2), "volume": 5000,
        })
        ts += timedelta(minutes=1)
    # Pullback through the gap zone
    for i in range(15):
        px -= random.uniform(0.3, 1.5)
        bars.append({
            "timestamp": ts, "open": round(px, 2), "high": round(px + 1, 2),
            "low": round(px - 0.5, 2), "close": round(px, 2), "volume": 5000,
        })
        ts += timedelta(minutes=1)

    return bars
