"""News Candle detection.

For each high-impact news event, extract the 1m candle at the exact
release time and track whether its high/low is subsequently taken.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from src.detection.models import NewsCandleInstance


def detect(
    bars: list[dict], instrument: str, trade_date: date,
    news_events: list[dict]
) -> list[NewsCandleInstance]:
    """Detect news candle instances for a given day.

    Args:
        bars: all 1m bars for the trading day, sorted ascending.
        instrument: e.g. "ES"
        trade_date: trading date
        news_events: list of dicts from news_events table.
                     Each has: event_name, event_time, impact, currency

    Returns list of NewsCandleInstance.
    """
    if not bars or not news_events:
        return []

    instances: list[NewsCandleInstance] = []

    for event in news_events:
        event_time = event.get("event_time")
        if event_time is None:
            continue
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        news_bar = None
        for b in bars:
            b_ts = _to_dt(b["timestamp"])
            if abs((b_ts - event_time).total_seconds()) < 90:
                news_bar = b
                break

        if news_bar is None:
            continue

        n_open = Decimal(str(news_bar["open"]))
        n_high = Decimal(str(news_bar["high"]))
        n_low = Decimal(str(news_bar["low"]))
        n_close = Decimal(str(news_bar["close"]))

        high_taken = False
        low_taken = False
        high_taken_time: Optional[datetime] = None
        low_taken_time: Optional[datetime] = None
        side_first: Optional[str] = None

        bar_idx = bars.index(news_bar)
        subsequent = bars[bar_idx + 1:]

        for sb in subsequent:
            sb_high = Decimal(str(sb["high"]))
            sb_low = Decimal(str(sb["low"]))

            if not high_taken and sb_high > n_high:
                high_taken = True
                high_taken_time = _to_dt(sb["timestamp"])
                if side_first is None:
                    side_first = "high"

            if not low_taken and sb_low < n_low:
                low_taken = True
                low_taken_time = _to_dt(sb["timestamp"])
                if side_first is None:
                    side_first = "low"

            if high_taken and low_taken:
                break

        if high_taken and low_taken:
            side_first = "both" if side_first is None else side_first

        post_mag = None
        if side_first and subsequent:
            sub_high = max(Decimal(str(sb["high"])) for sb in subsequent)
            sub_low = min(Decimal(str(sb["low"])) for sb in subsequent)
            post_mag = max(sub_high - n_high, n_low - sub_low)

        instances.append(NewsCandleInstance(
            instrument=instrument,
            event_name=event["event_name"],
            event_time=event_time,
            impact=event.get("impact", "high"),
            currency=event.get("currency", "USD"),
            open=n_open, high=n_high, low=n_low, close=n_close,
            high_taken=high_taken, low_taken=low_taken,
            high_taken_time=high_taken_time, low_taken_time=low_taken_time,
            side_taken_first=side_first or "neither",
            post_take_magnitude_pts=post_mag,
        ))

    return instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromtimestamp(ts)
