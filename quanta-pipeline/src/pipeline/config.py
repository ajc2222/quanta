"""Read env vars once, validate, export frozen config object."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Config:
    databento_api_key: str
    supabase_database_url: str
    port: int = 8080
    log_level: str = "INFO"
    run_nightly: bool = True
    run_intraday: bool = True

    # Timezone for all scheduling
    et_tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("America/New_York"))

    # Instruments tracked on CME Globex
    futures_instruments: tuple = ("ES", "NQ", "GC", "CL", "MES", "MNQ")

    # Options underlyings
    options_underlyings: tuple = ("^SPX", "^NDX")

    # Intraday options pull window (ET)
    options_start_time: str = "09:00"
    options_end_time: str = "16:30"
    options_interval_minutes: int = 30

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            databento_api_key=os.environ["DATABENTO_API_KEY"],
            supabase_database_url=os.environ["SUPABASE_DATABASE_URL"],
            port=int(os.getenv("PORT", "8080")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            run_nightly=os.getenv("RUN_NIGHTLY", "true").lower() == "true",
            run_intraday=os.getenv("RUN_INTRADAY", "true").lower() == "true",
        )
