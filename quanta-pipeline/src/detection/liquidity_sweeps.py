"""Buy-side Liquidity (BSL) and Sell-side Liquidity (SSL) detection per session.

BSL = swing high (prior session high). SSL = swing low (prior session low).
A sweep occurs when price exceeds the level during the session.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional

from src.detection.models import LiquidityLevel


SESSION_DEFS = {
    "asian":    (time(18, 0), time(3, 0)),
    "london":   (time(3, 0), time(9, 30)),
    "ny_am":    (time(9, 30), time(12, 0)),
    "ny_pm":    (time(12, 0), time(16, 0)),
    "overnight":(time(16, 0), time(18, 0)),
}


def find_swing_highs(bars: list[dict], window: int = 5) -> list[Decimal]:
    """Identify swing highs: bars whose high is higher than window bars on each side."""
    highs: list[Decimal] = []
    for i in range(window, len(bars) - window):
        is_swing = True
        for offset in range(1, window + 1):
            if bars[i]["high"] <= bars[i - offset]["high"] or bars[i]["high"] <= bars[i + offset]["high"]:
                is_swing = False
                break
        if is_swing:
            highs.append(Decimal(str(bars[i]["high"])))
    return highs


def find_swing_lows(bars: list[dict], window: int = 5) -> list[Decimal]:
    """Identify swing lows: bars whose low is lower than window bars on each side."""
    lows: list[Decimal] = []
    for i in range(window, len(bars) - window):
        is_swing = True
        for offset in range(1, window + 1):
            if bars[i]["low"] >= bars[i - offset]["low"] or bars[i]["low"] >= bars[i + offset]["low"]:
                is_swing = False
                break
        if is_swing:
            lows.append(Decimal(str(bars[i]["low"])))
    return lows


def detect(
    bars: list[dict], instrument: str, trade_date: date,
    prior_session_high: Optional[Decimal] = None,
    prior_session_low: Optional[Decimal] = None,
) -> list[LiquidityLevel]:
    """Detect BSL/SSL levels and whether they were swept during the session.

    Args:
        bars: OHLCV dicts for the trading day, sorted ascending.
        instrument: e.g. "ES"
        trade_date: the trading date
        prior_session_high: highest price from prior session (for BSL)
        prior_session_low: lowest price from prior session (for SSL)

    Returns list of LiquidityLevel.
    """
    levels: list[LiquidityLevel] = []

    swing_highs = find_swing_highs(bars)
    swing_lows = find_swing_lows(bars)

    for sh_price in swing_highs:
        swept = any(Decimal(str(b["high"])) > sh_price for b in bars)
        sweep_time = None
        post_dir = None
        if swept:
            for b in bars:
                if Decimal(str(b["high"])) > sh_price:
                    sweep_time = b["timestamp"]
                    break
            sweep_idx = next(i for i, b in enumerate(bars) if Decimal(str(b["high"])) > sh_price)
            if sweep_idx < len(bars) - 1:
                post_dir = "bearish" if bars[sweep_idx + 1]["close"] < bars[sweep_idx]["close"] else "bullish"

        levels.append(LiquidityLevel(
            instrument=instrument, session="ny_am", level_type="bsl",
            price=sh_price,
            swing_high_time=bars[0]["timestamp"], swing_low_time=bars[0]["timestamp"],
            swept=swept, sweep_time=sweep_time, post_sweep_direction=post_dir,
        ))

    for sl_price in swing_lows:
        swept = any(Decimal(str(b["low"])) < sl_price for b in bars)
        sweep_time = None
        post_dir = None
        if swept:
            for b in bars:
                if Decimal(str(b["low"])) < sl_price:
                    sweep_time = b["timestamp"]
                    break
            sweep_idx = next(i for i, b in enumerate(bars) if Decimal(str(b["low"])) < sl_price)
            if sweep_idx < len(bars) - 1:
                post_dir = "bullish" if bars[sweep_idx + 1]["close"] > bars[sweep_idx]["close"] else "bearish"

        levels.append(LiquidityLevel(
            instrument=instrument, session="ny_am", level_type="ssl",
            price=sl_price,
            swing_high_time=bars[0]["timestamp"], swing_low_time=bars[0]["timestamp"],
            swept=swept, sweep_time=sweep_time, post_sweep_direction=post_dir,
        ))

    if prior_session_high is not None:
        swept = any(Decimal(str(b["high"])) > prior_session_high for b in bars)
        levels.append(LiquidityLevel(
            instrument=instrument, session="ny_am", level_type="bsl",
            price=prior_session_high,
            swing_high_time=bars[0]["timestamp"], swing_low_time=bars[0]["timestamp"],
            swept=swept,
        ))
    if prior_session_low is not None:
        swept = any(Decimal(str(b["low"])) < prior_session_low for b in bars)
        levels.append(LiquidityLevel(
            instrument=instrument, session="ny_am", level_type="ssl",
            price=prior_session_low,
            swing_high_time=bars[0]["timestamp"], swing_low_time=bars[0]["timestamp"],
            swept=swept,
        ))

    return levels
