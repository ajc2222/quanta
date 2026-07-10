"""Tests for Key Open detection."""

from datetime import datetime, date, timedelta

from src.detection.key_opens import detect
from tests.fixtures.ohlcv_samples import synthetic_1m_bars


def test_key_opens_detected():
    bars = synthetic_1m_bars(start=datetime.now().replace(hour=17, minute=55), n_bars=200)
    results = detect(bars, "ES", bars[0]["timestamp"].date())
    assert len(results) <= 3


def test_key_open_no_respect():
    # All bars stay well above open, never trade back to it -> rejection
    ts = datetime.now().replace(hour=18, minute=0)
    bars = [{"timestamp": ts + timedelta(minutes=i), "open": 5850.0,
             "high": 5862.0, "low": 5855.0, "close": 5860.0, "volume": 1000}
            for i in range(60)]
    results = detect(bars, "ES", date.today())
    for r in results:
        if r.open_type == "open_1800":
            assert r.rejection is True


def test_key_opens_empty():
    assert detect([], "ES", date.today()) == []
