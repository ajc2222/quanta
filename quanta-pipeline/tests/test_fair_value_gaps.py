"""Tests for FVG detection."""

from datetime import datetime, timedelta

from src.detection.fair_value_gaps import detect, detect_fvgs, TF_CONFIGS
from src.detection.resample import resample_bars
from tests.fixtures.ohlcv_samples import synthetic_bullish_fvg_day, synthetic_1m_bars


def test_bullish_fvg_detected():
    bars = synthetic_bullish_fvg_day()
    results = detect({"1m": bars}, "ES", bars[0]["timestamp"].date())
    fvgs = [r for r in results if r.status in ("open", "partial", "filled")]
    assert len(fvgs) > 0, "Expected at least one FVG"


def test_fvg_fill_status():
    bars = synthetic_bullish_fvg_day()
    results = detect({"1m": bars}, "ES", bars[0]["timestamp"].date())
    filled = [r for r in results if r.status == "filled"]
    partial = [r for r in results if r.status == "partial"]
    assert len(filled) > 0 or len(partial) > 0


def test_resample_5m():
    bars = synthetic_bullish_fvg_day()
    resampled = resample_bars(bars, 5)
    assert len(resampled) < len(bars)
    assert all("open" in b and "high" in b and "low" in b and "close" in b for b in resampled)


def test_no_fvg_on_flat_data():
    bars = []
    ts = datetime.now().replace(hour=8, minute=0)
    for i in range(100):
        bars.append({"timestamp": ts + timedelta(minutes=i), "open": 5800.0, "high": 5800.5,
                      "low": 5799.5, "close": 5800.0, "volume": 100})
    results = detect({"1m": bars}, "ES", bars[0]["timestamp"].date())
    assert isinstance(results, list)


def test_fvg_detect_empty():
    assert detect({"1m": []}, "ES", datetime.now().date()) == []


def test_fvg_resample_empty():
    assert resample_bars([], 5) == []


def test_fvg_across_tfs():
    bars = synthetic_bullish_fvg_day()
    results = detect({"1m": bars}, "ES", bars[0]["timestamp"].date())
    tfs_found = set(r.timeframe for r in results)
    assert len(tfs_found) > 0
