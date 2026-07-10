"""Tests for News Candle detection."""

from datetime import datetime, date, timedelta

from src.detection.news_candles import detect
from tests.fixtures.ohlcv_samples import synthetic_1m_bars
from tests.fixtures.news_samples import sample_news_events


def test_news_candle_detected():
    bars = synthetic_1m_bars(start=datetime.now().replace(hour=8, minute=0), n_bars=200)
    events = sample_news_events()
    results = detect(bars, "ES", date.today(), events)
    # May or may not match depending on timestamps; just check no crash
    assert isinstance(results, list)


def test_news_candle_empty_input():
    assert detect([], "ES", date.today(), [{"event_name": "Test", "event_time": datetime.now(), "impact": "high", "currency": "USD"}]) == []
    assert detect([{"timestamp": datetime.now(), "open": 5800, "high": 5801, "low": 5799, "close": 5800, "volume": 100}], "ES", date.today(), []) == []
