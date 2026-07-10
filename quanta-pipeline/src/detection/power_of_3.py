"""Power of 3 phase classification - the flagship detector.

Classifies each of 7 time windows as BULLISH, BEARISH, or UNCONFIRMED
based on manipulation and distribution rules.
"""

from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from src.detection.models import PO3Instance


ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


WINDOW_DEFS: list[tuple[str, int, int, int]] = [
    ("daily",      18, 0,  23 * 60 + 60),
    ("4h_6am",      6, 0,  240),
    ("4h_10am",    10, 0,  240),
    ("30m_930",     9, 30,  30),
    ("30m_1000",   10, 0,   30),
    ("ny_session",  9, 30,  90),
    ("15m_945",     9, 45,  15),
]

NEWS_EARLY_START = {"start_hour": 8, "start_min": 30, "duration_min": 150}


def classify_window(bars: list[dict], instrument: str, window_type: str,
                    trade_date: date, window_start_dt: datetime, window_end_dt: datetime,
                    news_flag: bool = False) -> PO3Instance:
    """Classify a single PO3 window."""
    if not bars:
        return _empty_instance(instrument, window_type, trade_date, window_start_dt, window_end_dt)

    open_px = Decimal(str(bars[0]["open"]))
    high = max(Decimal(str(b["high"])) for b in bars)
    low = min(Decimal(str(b["low"])) for b in bars)
    close_px = Decimal(str(bars[-1]["close"]))

    hod_bar = max(bars, key=lambda b: b["high"])
    lod_bar = min(bars, key=lambda b: b["low"])
    hod = Decimal(str(hod_bar["high"]))
    lod = Decimal(str(lod_bar["low"]))
    hod_time = hod_bar["timestamp"]
    lod_time = lod_bar["timestamp"]

    window_duration = len(bars)
    first_40pct_cutoff = max(1, int(window_duration * 0.4))
    first_40pct = bars[:first_40pct_cutoff]

    first_40pct_low = min(Decimal(str(b["low"])) for b in first_40pct)
    first_40pct_high = max(Decimal(str(b["high"])) for b in first_40pct)

    threshold_pts = open_px * Decimal("0.0002")
    total_range = high - low
    manip_depth = None
    manip_start = None
    close_in_upper = None

    if total_range > 0:
        down_move = open_px - first_40pct_low
        up_move = first_40pct_high - open_px
        close_position_pct = float((close_px - low) / total_range) * 100

        if down_move >= threshold_pts and close_px > open_px and close_position_pct >= 60:
            phase = "bullish"
            manip_depth = float(down_move / open_px * 100)
            close_in_upper = True
            for b in first_40pct:
                if Decimal(str(b["low"])) == first_40pct_low:
                    manip_start = b["timestamp"]
                    break

        elif up_move >= threshold_pts and close_px < open_px and close_position_pct <= 40:
            phase = "bearish"
            manip_depth = float(up_move / open_px * 100)
            close_in_upper = False
            for b in first_40pct:
                if Decimal(str(b["high"])) == first_40pct_high:
                    manip_start = b["timestamp"]
                    break
        else:
            phase = "unconfirmed"
    else:
        phase = "unconfirmed"

    return PO3Instance(
        instrument=instrument, window_type=window_type, date=trade_date,
        window_start=window_start_dt, window_end=window_end_dt,
        open=open_px, high=high, low=low, close=close_px,
        hod=hod, hod_time=hod_time, lod=lod, lod_time=lod_time,
        phase=phase, manip_depth_pct=manip_depth,
        manip_start_time=manip_start, close_in_upper_pct=close_in_upper,
        news_flag=news_flag,
    )


def _empty_instance(instrument: str, window_type: str, trade_date: date,
                    w_start: datetime, w_end: datetime) -> PO3Instance:
    return PO3Instance(
        instrument=instrument, window_type=window_type, date=trade_date,
        window_start=w_start, window_end=w_end,
        open=Decimal("0"), high=Decimal("0"), low=Decimal("0"), close=Decimal("0"),
        hod=Decimal("0"), hod_time=w_start, lod=Decimal("0"), lod_time=w_start,
        phase="unconfirmed",
    )


def detect_for_day(
    bars: list[dict], instrument: str, trade_date: date,
    news_flag: bool = False, has_830_news: bool = False
) -> list[PO3Instance]:
    """Run PO3 classification for all 7 windows on a given day.

    Args:
        bars: all intraday 1m bars for the trading day, sorted.
        instrument: e.g. "ES"
        trade_date: date of the trading day
        news_flag: any high-impact news today
        has_830_news: specifically 8:30 ET news (affects NY session start)

    Returns list of 7 PO3Instance (one per window).
    """
    instances: list[PO3Instance] = []

    for w_type, start_h, start_m, dur_m in WINDOW_DEFS:
        if w_type == "ny_session" and has_830_news:
            es = NEWS_EARLY_START
            w_start = datetime.combine(trade_date, time(es["start_hour"], es["start_min"]), tzinfo=ET)
            w_end = w_start + timedelta(minutes=es["duration_min"])
        else:
            w_start = datetime.combine(trade_date, time(start_h, start_m), tzinfo=ET)
            w_end = w_start + timedelta(minutes=dur_m)

        w_start_utc = w_start.astimezone(UTC)
        w_end_utc = w_end.astimezone(UTC)

        window_bars = [
            b for b in bars
            if w_start_utc <= _to_dt(b["timestamp"]) < w_end_utc
        ]

        inst = classify_window(window_bars, instrument, w_type, trade_date,
                               w_start_utc, w_end_utc, news_flag)
        instances.append(inst)

    return instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=ET)
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromtimestamp(ts)
