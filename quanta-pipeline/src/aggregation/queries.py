"""Report-specific query builders that call into the generic aggregator."""

import logging
from datetime import date
from typing import Optional
from supabase import Client

from aggregation.aggregator import (
    build_report,
    FVG_METRICS, OB_METRICS, PO3_METRICS,
    LIQUIDITY_METRICS, KEYOPEN_METRICS, NEWS_CANDLE_METRICS,
    MACRO_METRICS, OPENING_GAP_METRICS, GEX_METRICS,
)

log = logging.getLogger(__name__)

REPORT_CONFIG = {
    "fvg":              ("fvg_instances", FVG_METRICS),
    "order_blocks":     ("order_block_instances", OB_METRICS),
    "liquidity":        ("liquidity_levels", LIQUIDITY_METRICS),
    "po3":              ("po3_instances", PO3_METRICS),
    "key_opens":        ("key_opens", KEYOPEN_METRICS),
    "news_candles":     ("news_candle_instances", NEWS_CANDLE_METRICS),
    "macros":           ("macro_instances", MACRO_METRICS),
    "opening_gaps":     ("opening_gap_instances", OPENING_GAP_METRICS),
    "gex":              ("gex_levels_daily", GEX_METRICS),
}

LOOKBACKS = [63, 126, 252]

INSTRUMENTS = ["ES", "NQ", "GC", "CL", "MES", "MNQ"]


def build_all_reports(db: Client, end_date: Optional[date] = None) -> list[dict]:
    """Build all report x instrument x lookback combinations.

    Returns flat list of dicts ready to insert into report_*_stats tables.
    """
    end = end_date or date.today()
    all_results: list[dict] = []

    for report_name, (table, metrics) in REPORT_CONFIG.items():
        instruments = INSTRUMENTS if report_name != "gex" else ["SPX", "NDX"]

        for instrument in instruments:
            for lb in LOOKBACKS:
                try:
                    results = build_report(report_name, instrument, lb, table, metrics, db, end)
                    all_results.extend([_result_to_dict(r, report_name) for r in results])
                except Exception:
                    log.error("Report build failed for %s %s lookback=%d", report_name, instrument, lb, exc_info=True)
                    continue

    return all_results


def _result_to_dict(r, report_name: str) -> dict:
    return {
        "report_type": report_name,
        "instrument": r.instrument,
        "lookback_days": r.lookback_days,
        "slice_key": r.slice_key,
        "metric_name": r.metric_name,
        "value": r.value,
        "sample_size": r.sample_size,
        "computed_at": r.computed_at.isoformat(),
    }
