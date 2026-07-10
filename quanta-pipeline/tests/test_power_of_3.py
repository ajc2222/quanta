"""Tests for PO3 classification."""

from datetime import datetime, date, timedelta, time

from src.detection.power_of_3 import detect_for_day, classify_window, WINDOW_DEFS
from tests.fixtures.ohlcv_samples import synthetic_1m_bars


def _make_manip_bars(open_px: float, bullish: bool) -> list[dict]:
    """Craft a synthetic window with clear bullish or bearish PO3."""
    bars = []
    ts = datetime.now().replace(hour=9, minute=30, second=0)
    n_bars = 30

    if bullish:
        for i in range(12):
            low = open_px - 3.0 - (i * 0.5)
            bars.append({"timestamp": ts + timedelta(minutes=i),
                          "open": open_px, "high": open_px - 1.0,
                          "low": low, "close": low + 0.5, "volume": 5000})
        offset = 12
        for i in range(offset, n_bars):
            close = open_px + 2.0 + (i - offset)
            bars.append({"timestamp": ts + timedelta(minutes=i),
                          "open": open_px, "high": close + 1.0,
                          "low": open_px - 0.5, "close": close,
                          "volume": 5000})
    else:
        for i in range(12):
            high = open_px + 3.0 + (i * 0.5)
            bars.append({"timestamp": ts + timedelta(minutes=i),
                          "open": open_px, "high": high,
                          "low": open_px + 1.0, "close": high - 0.5,
                          "volume": 5000})
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
    assert ny_session.news_flag is True


def test_po3_empty_window():
    """Window with no bars should return unconfirmed."""
    trade_date = date.today()
    w_start = datetime.combine(trade_date, time(3, 0))
    w_end = datetime.combine(trade_date, time(4, 0))
    inst = classify_window([], "ES", "4h_6am", trade_date, w_start, w_end)
    assert inst.phase == "unconfirmed"
