"""Key Open detection.

Tracks price behavior at 18:00 ET (Globex open), 00:00 ET (Midnight),
and 10:00 ET (Late morning). Determines if price returned to (respected)
or rejected each open level within the session.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional

from src.detection.models import KeyOpenInstance


KEY_OPEN_DEFS: list[tuple[str, time]] = [
    ("open_1800", time(18, 0)),
    ("open_0000", time(0, 0)),
    ("open_1000", time(10, 0)),
]


def detect(bars: list[dict], instrument: str, trade_date: date) -> list[KeyOpenInstance]:
    """Detect key open level interactions for a trading day."""
    if not bars:
        return []

    instances: list[KeyOpenInstance] = []
    session_high = max(Decimal(str(b["high"])) for b in bars)
    session_low = min(Decimal(str(b["low"])) for b in bars)

    for open_type, open_time in KEY_OPEN_DEFS:
        open_bars = [
            b for b in bars
            if _to_dt(b["timestamp"]).time() >= open_time
        ]
        if not open_bars:
            continue

        open_bar = open_bars[0]
        open_price = Decimal(str(open_bar["open"]))

        post_open_bars = open_bars[1:] if len(open_bars) > 1 else []
        if not post_open_bars:
            instances.append(KeyOpenInstance(
                instrument=instrument, date=trade_date,
                open_type=open_type, open_price=open_price,
                session_high=session_high, session_low=session_low,
            ))
            continue

        deviation_before = Decimal("0")
        time_to_test = None
        reversal_mag = Decimal("0")
        respected = False
        rejection = True

        for i, b in enumerate(post_open_bars):
            bh = Decimal(str(b["high"]))
            bl = Decimal(str(b["low"]))

            if bl <= open_price <= bh:
                respected = True
                rejection = False
                time_to_test = i + 1
                remaining = post_open_bars[i + 1:] if i + 1 < len(post_open_bars) else []
                if remaining:
                    after_high = max(Decimal(str(rb["high"])) for rb in remaining)
                    after_low = min(Decimal(str(rb["low"])) for rb in remaining)
                    reversal_mag = max(abs(after_high - open_price), abs(after_low - open_price))
                break
            else:
                deviation = min(abs(bh - open_price), abs(bl - open_price))
                if deviation > deviation_before:
                    deviation_before = deviation

        instances.append(KeyOpenInstance(
            instrument=instrument, date=trade_date,
            open_type=open_type, open_price=open_price,
            session_high=session_high, session_low=session_low,
            respected=respected, rejection=rejection,
            time_to_test=time_to_test,
            deviation_before_test_pts=deviation_before,
            reversal_magnitude_pts=reversal_mag if respected else None,
        ))

    return instances


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromtimestamp(ts)
