"""Opening Gap detection: NDOG and NWOG.

NDOG (New Day Opening Gap): prior day 17:00 close vs current 18:00 globex open
NWOG (New Week Opening Gap): Friday 17:00 close vs Sunday globex open
"""

from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional

from src.detection.models import OpeningGapInstance


def detect_ndog(
    bars_today: list[dict], bars_yesterday: list[dict],
    instrument: str, trade_date: date
) -> Optional[OpeningGapInstance]:
    """Detect NDOG: prior day 17:00 close -> today 18:00 open."""
    if not bars_today or not bars_yesterday:
        return None

    yest_1700 = trade_date - timedelta(days=1)
    yest_1700_dt = datetime.combine(yest_1700, time(17, 0))
    yest_close_bars = [
        b for b in bars_yesterday
        if _to_dt(b["timestamp"]) <= yest_1700_dt
    ]
    if not yest_close_bars:
        return None
    prior_close = Decimal(str(yest_close_bars[-1]["close"]))

    today_1800 = datetime.combine(trade_date, time(18, 0))
    today_open_bars = [
        b for b in bars_today
        if _to_dt(b["timestamp"]) >= today_1800
    ]
    if not today_open_bars:
        return None
    current_open = Decimal(str(today_open_bars[0]["open"]))

    gap_direction = "bullish" if current_open > prior_close else "bearish"
    gap_size = abs(current_open - prior_close)

    fill_pct, fill_time, fill_status, session_of_fill = _check_gap_fill(
        bars_today, prior_close, current_open, gap_direction
    )

    return OpeningGapInstance(
        instrument=instrument, gap_type="ndog", gap_date=trade_date,
        prior_close_price=prior_close, current_open_price=current_open,
        gap_direction=gap_direction, gap_size_pts=gap_size,
        fill_time=fill_time, fill_status=fill_status,
        fill_pct=fill_pct, session_of_fill=session_of_fill,
    )


def detect_nwog(
    bars_sunday: list[dict], bars_friday: list[dict],
    instrument: str, trade_date: date
) -> Optional[OpeningGapInstance]:
    """Detect NWOG: Friday 17:00 close -> Sunday globex open."""
    return detect_ndog(bars_sunday, bars_friday, instrument, trade_date)


def _check_gap_fill(
    bars: list[dict], prior_close: Decimal, current_open: Decimal, direction: str
) -> tuple[Optional[float], Optional[datetime], str, Optional[str]]:
    if not bars:
        return None, None, "open", None

    total_range = float(abs(current_open - prior_close))
    if total_range <= 0:
        return 100.0, bars[0]["timestamp"], "filled", None

    max_pct = 0.0
    fill_time: Optional[datetime] = None
    session_of_fill = None

    for b in bars:
        b_low = float(b["low"])
        b_high = float(b["high"])
        fill_low = float(min(prior_close, current_open))
        fill_high = float(max(prior_close, current_open))

        if b_high >= fill_low and b_low <= fill_high:
            penetration = min(b_high, fill_high) - max(b_low, fill_low)
            pct = penetration / total_range * 100
            if pct > max_pct:
                max_pct = pct
                fill_time = _to_dt(b["timestamp"])
                session_of_fill = _classify_session(fill_time)

            if b_low <= fill_low and b_high >= fill_high:
                return 100.0, fill_time, "filled", session_of_fill

    if max_pct > 0:
        return min(max_pct, 99.9), fill_time, "partial", session_of_fill
    return None, None, "open", None


def _classify_session(dt: datetime) -> str:
    h = dt.hour
    if 3 <= h < 9.5:
        return "london"
    if 9.5 <= h < 12:
        return "ny_am"
    if 12 <= h < 16:
        return "ny_pm"
    if 16 <= h < 18:
        return "overnight"
    return "asian"


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromtimestamp(ts)
