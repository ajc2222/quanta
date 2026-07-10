"""Entry point: scheduler + health server.

Schedule (ET):
  - Nightly 18:30: Databento + ForexFactory
  - Intraday 09:00-16:30 every 30 min: yfinance options + GEX
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Config
from .db import init_pool
from .ingestion import databento_ingest, forexfactory_ingest, yfinance_ingest
from .logging_setup import setup_logging
from .monitoring.health import serve

log = logging.getLogger("pipeline")


def _nightly_job(cfg: Config, status_store: dict) -> None:
    """Nightly batch: Databento incremental + ForexFactory."""
    log.info("=== NIGHTLY JOB START ===")

    # Databento — backfill instruments that have no data, nightly for rest
    for sym in cfg.futures_instruments:
        from .db import get_latest_bar_timestamp

        latest = get_latest_bar_timestamp(sym)
        if latest is None:
            log.info("No data for %s — running backfill", sym)
            databento_ingest.run_instrument_backfill(cfg, sym)
        else:
            databento_ingest.run_instrument_nightly(cfg, sym)

    forexfactory_ingest.run(cfg)

    status_store["last_nightly"] = time.time()
    log.info("=== NIGHTLY JOB DONE ===")


def _intraday_options_job(cfg: Config, status_store: dict) -> None:
    """Intraday yfinance options pull (runs every 30 min in window)."""
    log.info("=== INTRADAY OPTIONS ===")
    yfinance_ingest.run_all(cfg)
    status_store["last_intraday"] = time.time()
    log.info("=== INTRADAY OPTIONS DONE ===")


def main() -> None:
    cfg = Config.from_env()
    setup_logging(cfg.log_level)

    log.info("Quanta pipeline starting — nightly=%s intraday=%s",
             cfg.run_nightly, cfg.run_intraday)

    # Database
    init_pool(cfg.supabase_database_url)

    # Shared status store (read by /ready endpoint)
    status: dict = {
        "last_nightly": None,
        "last_intraday": None,
        "started_at": time.time(),
    }

    # Health check server (non-blocking)
    serve(cfg.port, status)

    # APScheduler
    scheduler = BackgroundScheduler(timezone=cfg.et_tz)

    if cfg.run_nightly:
        # Run at 18:30 ET weekdays
        scheduler.add_job(
            _nightly_job,
            trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=30, timezone=cfg.et_tz),
            args=[cfg, status],
            id="nightly",
            replace_existing=True,
        )
        log.info("Scheduled nightly: Mon-Fri 18:30 ET")

    if cfg.run_intraday:
        # Run every 30 min between 09:00 and 16:30 ET weekdays
        scheduler.add_job(
            _intraday_options_job,
            trigger=CronTrigger(day_of_week="mon-fri", hour="9-16", minute="0,30", timezone=cfg.et_tz),
            args=[cfg, status],
            id="intraday",
            replace_existing=True,
        )
        log.info("Scheduled intraday: Mon-Fri 09:00-16:30 ET, every 30 min")

    scheduler.start()

    # Graceful shutdown
    def _shutdown(signum, frame):
        log.info("Received signal %s, shutting down", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Keep alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        _shutdown(None, None)


if __name__ == "__main__":
    main()
