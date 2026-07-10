"""Tests for Opening Gap detection."""

from datetime import datetime, date, timedelta
from decimal import Decimal

from src.detection.opening_gaps import detect_ndog, detect_nwog


def _make_ndog_data(gap_up: bool = True) -> tuple[list[dict], list[dict]]:
    """Create today/yesterday bars with a clear opening gap."""
    yesterday = date.today() - timedelta(days=1)
    today = date.today()

    yest_ts = datetime.combine(yesterday, datetime.min.time())
    today_ts = datetime.combine(today, datetime.min.time())

    bars_yesterday = []
    # Simulate yesterday: close at 5795 around 17:00
    for i in range(60):
        t = yest_ts.replace(hour=16) + timedelta(minutes=i)
        bars_yesterday.append({
            "timestamp": t, "open": 5800.0, "high": 5802.0,
            "low": 5793.0, "close": 5795.0, "volume": 1000,
        })

    bars_today = []
    for i in range(60):
        t = today_ts.replace(hour=18) + timedelta(minutes=i)
        px = 5810.0 if gap_up else 5780.0
        bars_today.append({
            "timestamp": t, "open": px, "high": px + 2,
            "low": px - 1, "close": px + 0.5, "volume": 1000,
        })

    return bars_today, bars_yesterday


def test_ndog_detected():
    bars_today, bars_yesterday = _make_ndog_data(gap_up=True)
    result = detect_ndog(bars_today, bars_yesterday, "ES", date.today())
    assert result is not None
    assert result.gap_type == "ndog"
    assert result.gap_direction == "bullish"
    assert result.gap_size_pts > 0


def test_ndog_bearish_gap():
    bars_today, bars_yesterday = _make_ndog_data(gap_up=False)
    result = detect_ndog(bars_today, bars_yesterday, "ES", date.today())
    assert result is not None
    assert result.gap_direction == "bearish"


def test_ndog_empty_input():
    assert detect_ndog([], [], "ES", date.today()) is None
    assert detect_ndog([{"timestamp": datetime.now(), "open": 5800, "high": 5801, "low": 5799, "close": 5800, "volume": 100}], [], "ES", date.today()) is None


def test_nwog_delegates():
    # NWOG just delegates to NDOG so test it doesn't crash
    result = detect_nwog([], [], "ES", date.today())
    assert result is None
