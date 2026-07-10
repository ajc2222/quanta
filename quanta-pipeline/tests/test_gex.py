"""Tests for GEX computation."""

from datetime import date
from decimal import Decimal

from src.detection.gex import compute_gex


def _sample_snapshot() -> list[dict]:
    """Create a realistic SPX options chain snapshot."""
    strikes = [5500, 5550, 5600, 5650, 5700, 5750, 5800, 5850, 5900, 5950, 6000]
    snapshot = []
    for s in strikes:
        snapshot.append({
            "strike": s,
            "call_gamma": 0.0005 * (1 + (s - 5500) / 1000),
            "put_gamma": 0.0006 * (1 - (s - 5500) / 1000),
            "call_oi": 50000 + (s - 5500) * 100,
            "put_oi": 60000 - (s - 5500) * 100,
            "spot": 5800.0,
        })
    return snapshot


def test_gex_compute():
    snapshot = _sample_snapshot()
    result = compute_gex(snapshot, "SPX", date.today())
    assert result.underlying == "SPX"
    assert result.call_wall_strike > Decimal("0")
    assert result.put_wall_strike > Decimal("0")
    assert result.total_call_gex > 0
    assert result.total_put_gex > 0
    assert result.spot_price == Decimal("5800")
    assert result.max_pain_strike > Decimal("0")


def test_gex_empty_snapshot():
    result = compute_gex([], "SPX", date.today())
    assert result.underlying == "SPX"
    assert result.total_call_gex == 0.0
    assert result.total_put_gex == 0.0


def test_gex_ndx_multiplier():
    snapshot = _sample_snapshot()
    result = compute_gex(snapshot, "NDX", date.today())
    assert result.underlying == "NDX"
