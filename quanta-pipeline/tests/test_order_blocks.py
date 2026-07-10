"""Tests for Order Block detection."""

from datetime import datetime, timedelta
from decimal import Decimal

from src.detection.order_blocks import detect
from tests.fixtures.ohlcv_samples import synthetic_1m_bars


def _make_impulse_bars(bullish: bool = True) -> list[dict]:
    """Create bars with a clear impulse for OB detection."""
    ts = datetime.now().replace(hour=8, minute=0)
    bars = []

    # Build-up phase (5 bars)
    px = 5800.0
    for i in range(5):
        bars.append({"timestamp": ts + timedelta(minutes=i), "open": px, "high": px + 1,
                      "low": px - 1, "close": px - 0.5 if not bullish else px + 0.3,
                      "volume": 1000})
        px = bars[-1]["close"]

    # Last counter-trend bar (the OB)
    ob_idx = len(bars)
    if bullish:
        bars.append({"timestamp": ts + timedelta(minutes=ob_idx), "open": px, "high": px + 0.5,
                      "low": px - 2.0, "close": px - 1.5, "volume": 2000})
    else:
        bars.append({"timestamp": ts + timedelta(minutes=ob_idx), "open": px, "high": px + 2.0,
                      "low": px - 0.5, "close": px + 1.5, "volume": 2000})

    # Impulse (3+ bars in opposite direction)
    px = bars[-1]["close"]
    for i in range(3):
        j = len(bars)
        if bullish:
            bars.append({"timestamp": ts + timedelta(minutes=j), "open": float(px), "high": float(px) + 3 + i,
                          "low": float(px) - 0.5, "close": float(px) + 2 + i, "volume": 3000})
        else:
            bars.append({"timestamp": ts + timedelta(minutes=j), "open": float(px), "high": float(px) + 0.5,
                          "low": float(px) - 3 - i, "close": float(px) - 2 - i, "volume": 3000})
        px = bars[-1]["close"]

    return bars


def test_bullish_ob_detected():
    bars = _make_impulse_bars(bullish=True)
    results = detect(bars, "ES")
    bullish = [r for r in results if r.direction == "bullish"]
    assert len(bullish) > 0, "Expected a bullish OB"


def test_bearish_ob_detected():
    bars = _make_impulse_bars(bullish=False)
    results = detect(bars, "ES")
    bearish = [r for r in results if r.direction == "bearish"]
    assert len(bearish) > 0, "Expected a bearish OB"


def test_ob_empty_input():
    assert detect([], "ES") == []


def test_ob_too_few_bars():
    bars = [{"timestamp": datetime.now(), "open": 5800, "high": 5801, "low": 5799, "close": 5800, "volume": 100}]
    assert detect(bars, "ES") == []
