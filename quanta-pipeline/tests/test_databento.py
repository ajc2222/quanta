"""Tests for the Databento ingestion module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.pipeline.config import Config
from src.pipeline.ingestion.databento_ingest import (
    fetch_ohlcv_1m,
    run_all,
    run_instrument_backfill,
    run_instrument_nightly,
)


@pytest.fixture
def cfg() -> Config:
    return Config(
        databento_api_key="test_key",
        supabase_database_url="postgresql://test:test@localhost:6543/test",
        port=8080,
        log_level="DEBUG",
    )


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Return a synthetic DataFrame matching Databento's schema."""
    return pd.DataFrame({
        "ts_event": pd.date_range("2026-07-01", periods=5, freq="1min", tz="America/New_York"),
        "open": [4500.0] * 5,
        "high": [4510.0] * 5,
        "low": [4490.0] * 5,
        "close": [4505.0] * 5,
        "volume": [1000] * 5,
    })


def test_fetch_ohlcv_1m_returns_expected_columns(cfg, sample_df):
    with patch("src.pipeline.ingestion.databento_ingest.Historical") as MockHistorical:
        mock_instance = MockHistorical.return_value
        mock_instance.timesales.get_range.return_value = MagicMock()
        mock_instance.timesales.get_range.return_value.to_df.return_value = sample_df
        mock_instance.timesales.get_range.return_value.empty = False

        start = pd.Timestamp("2026-07-01", tz="America/New_York")
        end = pd.Timestamp("2026-07-02", tz="America/New_York")
        df = fetch_ohlcv_1m("test_key", "ES", start, end)

        assert not df.empty
        expected_cols = {"instrument", "timestamp", "open", "high", "low", "close", "volume"}
        assert expected_cols.issubset(set(df.columns))
        assert (df["instrument"] == "ES").all()


def test_fetch_ohlcv_1m_returns_empty_on_no_data(cfg):
    with patch("src.pipeline.ingestion.databento_ingest.Historical") as MockHistorical:
        mock_instance = MockHistorical.return_value
        mock_instance.timesales.get_range.return_value = None

        start = pd.Timestamp("2026-01-01", tz="America/New_York")
        end = pd.Timestamp("2026-01-02", tz="America/New_York")
        df = fetch_ohlcv_1m("test_key", "ES", start, end)

        assert df.empty


def test_nightly_with_existing_data_skips(cfg):
    with patch("src.pipeline.ingestion.databento_ingest.get_latest_bar_timestamp", return_value=pd.Timestamp("2026-07-01", tz="America/New_York")):
        result = run_instrument_backfill(cfg, "ES")
        assert result == 0


def test_nightly_runs_and_upserts(cfg):
    with (
        patch("src.pipeline.ingestion.databento_ingest.fetch_ohlcv_1m") as mock_fetch,
        patch("src.pipeline.ingestion.databento_ingest.upsert_ohlcv_1m", return_value=5) as mock_upsert,
    ):
        mock_fetch.return_value = pd.DataFrame({
            "instrument": ["ES"] * 5,
            "timestamp": pd.date_range("2026-07-01", periods=5, freq="1min", tz="America/New_York"),
            "open": [4500.0] * 5,
            "high": [4510.0] * 5,
            "low": [4490.0] * 5,
            "close": [4505.0] * 5,
            "volume": [1000] * 5,
        })
        result = run_instrument_nightly(cfg, "ES")
        assert result == 5
        mock_upsert.assert_called_once()


def test_run_all_continues_on_failure(cfg):
    with patch("src.pipeline.ingestion.databento_ingest.run_instrument_nightly", side_effect=ValueError("boom")):
        results = run_all(cfg, backfill=False)
        # Should still run for all 6 instruments
        assert len(results) == len(cfg.futures_instruments)
        for sym, count in results.items():
            assert count == -1  # sentinel for failure
