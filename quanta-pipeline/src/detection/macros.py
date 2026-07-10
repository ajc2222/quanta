"""Macro window classification.

5 windows: 9:50-10:10, 10:50-11:10, 1:10-1:40, 2:10-2:40, 3:15-4:00
Each window records direction, HOD/LOD, magnitude, and prior context.
"""

from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional

from src.detection.models import MacroInstance


MACRO_WINDOWS: list[tuple[str, time, time]] = [
    ("macro_950",  time(9, 50),  time(10, 10)),
    ("macro_1050", time(10, 50), time(11, 10)),
    ("macro_110",  time(13, 10), time(13, 40)),
    ("macro_210",  time(14, 10), time(14, 40)),
    ("macro_315",  time(15, 15), time(16, 0)),
]


def detect(
    bars_all: list[dict],
    instrument: str,
    trade_date: date,
    prior_context: Optional[dict] = None,
) -> list[MacroInstance]:
    """Detect macro window activity for a trading day."""
    if not bars_all:
        return []

    ctx = prior_context or {}
    instances: list[MacroInstance] = []

    day_high = max(Decimal(str(b["high"])) for b in bars_all)
    day_low = min(Decimal(str(b["low"])) for b in bars_all)

    pre_macro_bars = [
        b for b in bars_all
        if _to_dt(b["timestamp"]).time() < time(9, 50)
    ]
    hod_made_before = False
    lod_made_before = False
    if pre_macro_bars:
        pre_high = max(Decimal(str(b["high"])) for b in pre_macro_bars)
        pre_low = min(Decimal(str(b["low"])) for b in pre_macro_bars)
        if pre_high >= day_high:
            hod_made_before = True
        if pre_low <= day_low:
            lod_made_before = True

    for w_type, start_t, end_t in MACRO_WINDOWS:
        window_bars = [
            b for b in bars_all
            if start_t <= _to_dt(b["timestamp"]).time() < end_t
        ]
        if not window_bars:
            continue

        open_px = Decimal(str(window_bars[0]["open"]))
        high = max(Decimal(str(b["high"])) for b in window_bars)
        low = min(Decimal(str(b["low"])) for b in window_bars)
        close = Decimal(str(window_bars[-1]["close"]))
        magnitude = high - low

        hod_bar = max(window_bars, key=lambda b: b["high"])
        lod_bar = min(window_bars, key=lambda b: b["low"])
        hod = Decimal(str(hod_bar["high"]))
        lod = Decimal(str(lod_bar["low"]))
        hod_time = _to_dt(hod_bar["timestamp"])
        lod_time = _to_dt(lod_bar["timestamp"])

        if close > open_px and magnitude > 0:
            direction = "bullish"
        elif close < open_px and magnitude > 0:
            direction = "bearish"
        else:
            direction = "choppy"

        day_range = day_high - day_low
        if day_range > 0 and magnitude / day_range < Decimal("0.1"):
            direction = "choppy"

        instances.append(MacroInstance(
            instrument=instrument, window_type=w_type, date=trade_date,
            window_start=datetime.combine(trade_date, start_t),
            window_end=datetime.combine(trade_date, end_t),
            open=open_px, high=high, low=low, close=close,
            hod=hod, hod_time=hod_time, lod=lod, lod_time=lod_time,
            direction=direction, magnitude_pts=magnitude,
            hod_of_day_made=hod_made_before, lod_of_day_made=lod_made_before,
            preceding_po3_phase=ctx.get("preceding_po3_phase"),
            at_pd_array_open=ctx.get("at_pd_array_open"),
            news_flag=ctx.get("news_flag", False),
            london_direction=ctx.get("london_direction"),
            ny_open_30m_direction=ctx.get("ny_open_30m_direction"),
            gex_proximity=ctx.get("gex_proximity"),
        ))

    return instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromtimestamp(ts)
