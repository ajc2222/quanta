"""Order Block detection.

Bullish OB: the last down-close candle immediately before a bullish impulse
(3+ consecutive up-closes or a single bar with range > 2x average).
Bearish OB: the last up-close candle immediately before a bearish impulse.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.detection.models import OrderBlockInstance


def _impulse_start(bars: list[dict], idx: int, lookback: int = 3) -> Optional[int]:
    """Find the index of the candle just before a bullish impulse starts.

    Returns the index of the candle just before the impulse (the potential OB).
    """
    if idx < 1 or idx + lookback > len(bars):
        return None

    for offset in range(lookback):
        b = bars[idx + offset]
        if b["close"] <= b["open"]:
            return None
    return idx - 1


def _bearish_impulse_start(bars: list[dict], idx: int, lookback: int = 3) -> Optional[int]:
    """Find the index just before a bearish impulse starts."""
    if idx < 1 or idx + lookback > len(bars):
        return None
    for offset in range(lookback):
        b = bars[idx + offset]
        if b["close"] >= b["open"]:
            return None
    return idx - 1


def detect(bars: list[dict], instrument: str, timeframe: str = "15m") -> list[OrderBlockInstance]:
    """Detect order blocks in a series of bars.

    Args:
        bars: OHLCV dicts sorted ascending by time.
        instrument: e.g. "ES"
        timeframe: the bar timeframe (default 15m).

    Returns list of OrderBlockInstance.
    """
    instances: list[OrderBlockInstance] = []

    for i in range(1, len(bars)):
        # Bullish OB: last down-close candle before 3+ up-close impulse
        bulb_idx = _impulse_start(bars, i, lookback=3)
        if bulb_idx is not None:
            ob_candle = bars[bulb_idx]
            if ob_candle["close"] < ob_candle["open"]:
                instances.append(OrderBlockInstance(
                    instrument=instrument, timeframe=timeframe, direction="bullish",
                    origin_candle_time=ob_candle["timestamp"],
                    origin_open=Decimal(str(ob_candle["open"])),
                    origin_high=Decimal(str(ob_candle["high"])),
                    origin_low=Decimal(str(ob_candle["low"])),
                    origin_close=Decimal(str(ob_candle["close"])),
                ))
                continue

        # Bearish OB: last up-close candle before 3+ down-close impulse
        bear_idx = _bearish_impulse_start(bars, i, lookback=3)
        if bear_idx is not None:
            ob_candle = bars[bear_idx]
            if ob_candle["close"] > ob_candle["open"]:
                instances.append(OrderBlockInstance(
                    instrument=instrument, timeframe=timeframe, direction="bearish",
                    origin_candle_time=ob_candle["timestamp"],
                    origin_open=Decimal(str(ob_candle["open"])),
                    origin_high=Decimal(str(ob_candle["high"])),
                    origin_low=Decimal(str(ob_candle["low"])),
                    origin_close=Decimal(str(ob_candle["close"])),
                ))
                continue

    return instances
