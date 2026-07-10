"""Tests for the aggregation engine — pure functions, no DB needed."""

from datetime import datetime, date
from decimal import Decimal
import pandas as pd

from src.aggregation.aggregator import (
    MetricDef, AggregationResult,
    compute_rates, compute_averages, compute_distributions,
    aggregate_all, FVG_METRICS, PO3_METRICS,
)


def _fake_fvg_df() -> pd.DataFrame:
    """Create a synthetic FVG instances dataframe."""
    return pd.DataFrame([
        {"date": date(2026, 7, 1), "instrument": "ES", "timeframe": "1H",
         "status": "filled", "fill_pct": 100.0, "weekday": "Wed",
         "high": Decimal("5805"), "low": Decimal("5795")},
        {"date": date(2026, 7, 2), "instrument": "ES", "timeframe": "15m",
         "status": "filled", "fill_pct": 100.0, "weekday": "Thu",
         "high": Decimal("5810"), "low": Decimal("5798")},
        {"date": date(2026, 7, 3), "instrument": "ES", "timeframe": "1H",
         "status": "open", "fill_pct": 0.0, "weekday": "Fri",
         "high": Decimal("5800"), "low": Decimal("5790")},
    ])


def test_compute_rates():
    df = _fake_fvg_df()
    # Filter to "filled" status rows (like FVG_METRICS[0] does)
    df_filled = df[df["status"] == "filled"]
    results = compute_rates(df_filled, "fill_pct", ["timeframe"])
    assert len(results) > 0
    # Rate of True values: all non-zero fill_pct values are truthy -> rate = 1.0
    assert results[0].value == 1.0


def test_compute_averages():
    df = _fake_fvg_df()
    results = compute_averages(df, "fill_pct", ["timeframe"])
    assert len(results) > 0
    # Check 1H avg: (100 + 0) / 2 = 50
    for r in results:
        if "timeframe=1H" in r.slice_key:
            assert r.value == 50.0
            assert r.sample_size == 2


def test_aggregate_all():
    df = _fake_fvg_df()
    results = aggregate_all("fvg", "ES", 63, df, FVG_METRICS)
    assert len(results) > 0
    for r in results:
        assert r.report_type == "fvg"
        assert r.instrument == "ES"
        assert r.lookback_days == 63


def test_aggregate_empty_df():
    df = pd.DataFrame()
    results = aggregate_all("fvg", "ES", 63, df, FVG_METRICS)
    assert results == []


def test_po3_metrics():
    df = pd.DataFrame([
        {"date": date(2026, 7, 1), "instrument": "ES", "window_type": "30m_930",
         "phase": "bullish", "weekday": "Wed",
         "high": Decimal("5810"), "low": Decimal("5790"),
         "pd_array_held_hod": "fvg", "pd_array_held_lod": "none"},
        {"date": date(2026, 7, 2), "instrument": "ES", "window_type": "30m_930",
         "phase": "bearish", "weekday": "Thu",
         "high": Decimal("5805"), "low": Decimal("5795"),
         "pd_array_held_hod": "ob", "pd_array_held_lod": "none"},
    ])
    results = aggregate_all("po3", "ES", 63, df, PO3_METRICS)
    assert len(results) > 0
