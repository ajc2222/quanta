"""Quanta Detection Engine — market structure detectors.

Each module exposes a `detect()` function (or equivalent) that accepts
OHLCV bars and returns typed instance dataclasses. Detectors are pure;
the orchestrator handles DB writes.
"""

from src.detection import fair_value_gaps
from src.detection import order_blocks
from src.detection import liquidity_sweeps
from src.detection import power_of_3
from src.detection import key_opens
from src.detection import opening_gaps
from src.detection import news_candles
from src.detection import macros
from src.detection import gex
