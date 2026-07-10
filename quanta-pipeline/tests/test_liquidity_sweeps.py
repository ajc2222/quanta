"""Tests for BSL/SSL Liquidity Sweep detection."""

from datetime import datetime, date, timedelta
from decimal import Decimal

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
    assert any(r.swept for r in results)


def test_empty_bars():
    assert detect([], "ES", date.today()) == []


def test_prior_session_levels():
    bars = synthetic_1m_bars(n_bars=200, volatility=5.0)
    prior_high = Decimal("5850")
    prior_low = Decimal("5750")
    results = detect(bars, "ES", date.today(), prior_session_high=prior_high, prior_session_low=prior_low)
    # Should have swing highs from synthetic data + prior session levels
    bsl = [r for r in results if r.level_type == "bsl"]
    ssl = [r for r in results if r.level_type == "ssl"]
    assert any(r.price == prior_high for r in bsl)
    assert any(r.price == prior_low for r in ssl)
