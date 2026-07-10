"""Minimal typed containers for all detection instances.

Plain dataclasses — no ORM, no heavy framework. Used across all detectors
and the aggregator. Row-like for direct dict conversion via vars().
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


@dataclass
class FVGInstance:
    instrument: str
    timeframe: str
    high_bound: Decimal
    low_bound: Decimal
    creation_time: datetime
    creation_price: Decimal
    fill_time: Optional[datetime] = None
    fill_pct: Optional[float] = None
    status: str = "open"


@dataclass
class OrderBlockInstance:
    instrument: str
    timeframe: str
    direction: str
    origin_candle_time: datetime
    origin_open: Decimal
    origin_high: Decimal
    origin_low: Decimal
    origin_close: Decimal
    first_test_time: Optional[datetime] = None
    outcome: str = "untested"


@dataclass
class LiquidityLevel:
    instrument: str
    session: str
    level_type: str
    price: Decimal
    swing_high_time: datetime
    swing_low_time: datetime
    swept: bool = False
    sweep_time: Optional[datetime] = None
    post_sweep_direction: Optional[str] = None
    magnitude_pts: Optional[Decimal] = None


@dataclass
class PO3Instance:
    instrument: str
    window_type: str
    date: date
    window_start: datetime
    window_end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    hod: Decimal
    hod_time: datetime
    lod: Decimal
    lod_time: datetime
    phase: str
    manip_depth_pct: Optional[float] = None
    manip_start_time: Optional[datetime] = None
    close_in_upper_pct: Optional[bool] = None
    news_flag: bool = False
    pd_array_held_hod: Optional[str] = None
    pd_array_held_lod: Optional[str] = None
    pd_array_detail_hod: Optional[str] = None
    pd_array_detail_lod: Optional[str] = None


@dataclass
class KeyOpenInstance:
    instrument: str
    date: date
    open_type: str
    open_price: Decimal
    session_high: Decimal
    session_low: Decimal
    respected: bool = False
    rejection: bool = False
    time_to_test: Optional[int] = None
    deviation_before_test_pts: Optional[Decimal] = None
    reversal_magnitude_pts: Optional[Decimal] = None


@dataclass
class OpeningGapInstance:
    instrument: str
    gap_type: str
    gap_date: date
    prior_close_price: Decimal
    current_open_price: Decimal
    gap_direction: str
    gap_size_pts: Decimal
    fill_time: Optional[datetime] = None
    fill_status: str = "open"
    fill_pct: Optional[float] = None
    session_of_fill: Optional[str] = None


@dataclass
class NewsCandleInstance:
    instrument: str
    event_name: str
    event_time: datetime
    impact: str
    currency: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    high_taken: bool = False
    low_taken: bool = False
    high_taken_time: Optional[datetime] = None
    low_taken_time: Optional[datetime] = None
    side_taken_first: Optional[str] = None
    post_take_magnitude_pts: Optional[Decimal] = None


@dataclass
class MacroInstance:
    instrument: str
    window_type: str
    date: date
    window_start: datetime
    window_end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    hod: Decimal
    hod_time: datetime
    lod: Decimal
    lod_time: datetime
    direction: str
    magnitude_pts: Decimal
    hod_of_day_made: bool = False
    lod_of_day_made: bool = False
    preceding_po3_phase: Optional[str] = None
    at_pd_array_open: Optional[str] = None
    news_flag: bool = False
    london_direction: Optional[str] = None
    ny_open_30m_direction: Optional[str] = None
    gex_proximity: Optional[str] = None


@dataclass
class GEXLevelDaily:
    date: date
    underlying: str
    spot_price: Decimal
    call_wall_strike: Decimal
    put_wall_strike: Decimal
    max_pain_strike: Decimal
    gex_flip_strike: Optional[Decimal] = None
    zero_gamma_strike: Optional[Decimal] = None
    total_call_gex: float = 0.0
    total_put_gex: float = 0.0
    net_gex: float = 0.0
