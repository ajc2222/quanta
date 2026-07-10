"""Tests for the yfinance options/GEX ingestion module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.pipeline.config import Config
from src.pipeline.ingestion.yfinance_ingest import (
    _norm_pdf,
    compute_gamma,
    _compute_gex_snapshot,
    run_snapshot,
)


@pytest.fixture
def cfg() -> Config:
    return Config(
        databento_api_key="test_key",
        supabase_database_url="postgresql://test:test@localhost:6543/test",
    )


def test_norm_pdf():
    x = np.array([0.0])
    result = _norm_pdf(x)
    assert np.isclose(result[0], 0.39894228, atol=1e-6)


def test_compute_gamma_atm():
    # ATM option: S=K, T=30d, sigma=20%
    S = 5000.0
    K = np.array([5000.0])
    T = np.array([30.0 / 365.0])
    sigma = np.array([0.20])
    gamma = compute_gamma(S, K, T, sigma)
    assert gamma[0] > 0
    # ATM gamma should be in a reasonable range for SPX
    assert 0.001 < gamma[0] < 0.1


def test_compute_gamma_otm():
    # OTM call: S=5000, K=6000
    S = 5000.0
    K = np.array([6000.0])
    T = np.array([30.0 / 365.0])
    sigma = np.array([0.20])
    gamma = compute_gamma(S, K, T, sigma)
    assert gamma[0] > 0
    # OTM gamma should be lower than ATM
    atm_gamma = compute_gamma(5000.0, np.array([5000.0]), T, sigma)[0]
    assert gamma[0] < atm_gamma


def test_compute_gex_snapshot_basic():
    now = pd.Timestamp.now(tz="America/New_York")
    chain = pd.DataFrame({
        "strike": [5000.0, 5000.0, 5100.0, 5100.0],
        "option_type": ["call", "put", "call", "put"],
        "open_interest": [10000, 8000, 5000, 3000],
        "implied_volatility": [0.20, 0.21, 0.19, 0.20],
        "dte": [30, 30, 30, 30],
    })
    spot = 5050.0

    per_strike, summary = _compute_gex_snapshot(chain, spot, "SPX", now)

    assert len(per_strike) == 2  # two strikes
    assert summary["total_call_gex"] > 0
    assert summary["total_put_gex"] < 0  # puts are negative
    assert summary["spot_price"] == round(spot, 2)
    assert summary["underlying"] == "SPX"


def test_compute_gex_snapshot_empty_chain():
    now = pd.Timestamp.now(tz="America/New_York")
    chain = pd.DataFrame(columns=["strike", "option_type", "open_interest", "implied_volatility", "dte"])
    spot = 5000.0

    per_strike, summary = _compute_gex_snapshot(chain, spot, "SPX", now)
    assert per_strike == []
    assert summary == {}


def test_compute_gex_snapshot_detects_call_wall():
    now = pd.Timestamp.now(tz="America/New_York")
    chain = pd.DataFrame({
        "strike": [4900.0, 5000.0, 5100.0],
        "option_type": ["call", "call", "call"],
        "open_interest": [1000, 50000, 1000],
        "implied_volatility": [0.20, 0.20, 0.20],
        "dte": [30, 30, 30],
    })
    spot = 5000.0

    per_strike, summary = _compute_gex_snapshot(chain, spot, "SPX", now)
    assert summary["call_wall_strike"] == 5000.0


@patch("src.pipeline.ingestion.yfinance_ingest.yf.Ticker")
def test_run_snapshot_success(mock_ticker, cfg):
    """End-to-end test with mocked yfinance ticker."""
    mock_instance = mock_ticker.return_value

    # Mock history returning spot
    hist_df = pd.DataFrame({"Close": [5000.0, 5010.0]})
    mock_instance.history.return_value = hist_df

    # Mock options expiries
    mock_instance.options = ("2026-08-15",)

    # Mock option chain
    mock_chain = MagicMock()
    mock_chain.calls = pd.DataFrame({
        "strike": [5000.0, 5100.0],
        "openInterest": [10000, 5000],
        "volume": [500, 200],
        "impliedVolatility": [0.20, 0.19],
        "lastPrice": [150.0, 80.0],
    })
    mock_chain.puts = pd.DataFrame({
        "strike": [4900.0, 5000.0],
        "openInterest": [8000, 12000],
        "volume": [300, 600],
        "impliedVolatility": [0.21, 0.22],
        "lastPrice": [50.0, 100.0],
    })
    mock_instance.option_chain.return_value = mock_chain

    with (
        patch("src.pipeline.ingestion.yfinance_ingest.insert_options_snapshot", return_value=4),
        patch("src.pipeline.ingestion.yfinance_ingest.insert_gex_levels", return_value=4),
        patch("src.pipeline.ingestion.yfinance_ingest.upsert_gex_summary"),
    ):
        result = run_snapshot(cfg, "^SPX")

    assert result is not None
    assert result["underlying"] == "SPX"
    assert result["spot_price"] == 5010.0
    assert result["total_call_gex"] > 0
    assert result["total_put_gex"] < 0
