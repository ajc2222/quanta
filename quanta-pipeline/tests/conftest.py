"""Shared pytest fixtures."""

import pytest
from datetime import datetime
from decimal import Decimal

from tests.fixtures.ohlcv_samples import synthetic_1m_bars, synthetic_bullish_fvg_day
from tests.fixtures.news_samples import sample_news_events


@pytest.fixture
def sample_1m_bars():
    return synthetic_1m_bars()


@pytest.fixture
def sample_bullish_fvg_bars():
    return synthetic_bullish_fvg_day()


@pytest.fixture
def sample_news_events():
    return sample_news_events()
