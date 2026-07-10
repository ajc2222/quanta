"""Environment-based configuration for detection/aggregation pipeline.

All secrets via env vars, never hardcoded.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    supabase_url: str = field(default_factory=lambda: os.environ["SUPABASE_URL"])
    supabase_key: str = field(default_factory=lambda: os.environ["SUPABASE_SERVICE_KEY"])
    upstash_redis_url: Optional[str] = os.environ.get("UPSTASH_REDIS_URL")
    databento_api_key: Optional[str] = os.environ.get("DATABENTO_API_KEY")

    nightly_run_hour_utc: int = 23
    intraday_interval_minutes: int = 30

    po3_manipulation_threshold_pct: float = 0.02
    fvg_min_size_ticks: int = 1
    liquidity_sweep_proximity_ticks: int = 2

    lookback_windows: list[int] = field(default_factory=lambda: [63, 126, 252])

    @classmethod
    def load(cls) -> "Config":
        return cls()
