"""Tests for Macro window detection."""

from datetime import datetime, date, timedelta

from src.detection.macros import detect
from tests.fixtures.ohlcv_samples import synthetic_1m_bars


def test_macro_windows_detected():
    bars = synthetic_1m_bars(n_bars=780, start=datetime.now().replace(hour=6, minute=0))
    results = detect(bars, "ES", bars[0]["timestamp"].date())
    # Should find some macro windows with data
    assert len(results) > 0


def test_macro_with_context():
    bars = synthetic_1m_bars(n_bars=780, start=datetime.now().replace(hour=6, minute=0))
    ctx = {"news_flag": True, "preceding_po3_phase": "bullish"}
    results = detect(bars, "ES", bars[0]["timestamp"].date(), prior_context=ctx)
    assert any(r.news_flag for r in results)
    assert any(r.preceding_po3_phase == "bullish" for r in results)


def test_macro_empty_input():
    assert detect([], "ES", date.today()) == []
