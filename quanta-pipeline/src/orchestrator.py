"""Pipeline orchestrator. Runs Stage 2 (detection) then Stage 3 (aggregation).

Dependency order for detectors:
  1. News events (needed by PO3, Macros for news_flag)
  2. FVGs (needed for PD array correlation in PO3)
  3. OBs (needed for PD array correlation)
  4. BSL/SSL
  5. Key Opens
  6. Opening Gaps
  7. PO3 (depends on news_flag, FVGs, OBs for PD array matching)
  8. Macros (depends on PO3, news_flag, GEX)
  9. News Candles
  10. GEX (independent, can run last)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from config import Config
from db import get_db, insert_many, delete_old_instances, fetch_ohlcv
import detection
from aggregation.queries import build_all_reports, LOOKBACKS, INSTRUMENTS

log = logging.getLogger(__name__)

CONTEXT_DAYS = 5
ET = ZoneInfo("America/New_York")


def _instances_to_dicts(instances: list) -> list[dict]:
    """Convert dataclass instances to dicts for DB insertion."""
    return [vars(inst) for inst in instances]


def _to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromtimestamp(ts)


def _find_nearest_pd_array(price, fvg_instances, ob_instances, tolerance_pct: float = 0.0002) -> tuple[str, str]:
    """Find nearest PD array within tolerance. Returns (type, detail_json)."""
    for fvg in fvg_instances:
        if abs(float(fvg.high_bound - price)) / float(price) <= tolerance_pct:
            return ("fvg", '{"type":"fvg","tf":"%s","id":""}' % fvg.timeframe)
        if abs(float(fvg.low_bound - price)) / float(price) <= tolerance_pct:
            return ("fvg", '{"type":"fvg","tf":"%s","id":""}' % fvg.timeframe)

    for ob in ob_instances:
        ob_mid = (float(ob.origin_high) + float(ob.origin_low)) / 2.0
        if abs(ob_mid - float(price)) / float(price) <= tolerance_pct:
            return ("ob", '{"type":"ob","tf":"%s","id":""}' % ob.timeframe)

    return ("none", "")


def run_detection_day(instrument: str, trade_date: date, cfg: Config, db) -> dict:
    """Run all detectors for one instrument on one trading day.

    Returns dict of {table_name: [instance_dicts]} for insertion.
    """
    start = trade_date - timedelta(days=CONTEXT_DAYS)
    end = trade_date + timedelta(days=1)

    bars_1m = fetch_ohlcv(instrument, start.isoformat(), end.isoformat(), db)
    if not bars_1m:
        return {}

    for b in bars_1m:
        if isinstance(b.get("ts"), str):
            dt = datetime.fromisoformat(b["ts"].replace("Z", "+00:00"))
            b["ts"] = dt
            b["timestamp"] = dt  # detection modules use "timestamp" key

    bars_today = [
        b for b in bars_1m
        if _to_dt(b["timestamp"]).astimezone(ET).date() == trade_date
    ]
    bars_context = bars_1m

    # 1. Fetch news events for this day
    news_events = db.table("news_events") \
        .select("*") \
        .gte("event_time", trade_date.isoformat()) \
        .lte("event_time", (trade_date + timedelta(days=1)).isoformat()) \
        .execute()
    news_events = news_events.data or []

    news_flag = len(news_events) > 0
    has_830_news = any(
        "08:30" in (e.get("event_time", "") if isinstance(e.get("event_time"), str) else str(e.get("event_time", "")))
        for e in news_events
    ) or any(
        _to_dt(e["event_time"]).hour == 8 and _to_dt(e["event_time"]).minute == 30
        for e in news_events if "event_time" in e
    )

    # 2. Detect FVGs
    try:
        fvg_instances = detection.fair_value_gaps.detect(
            {"1m": bars_context}, instrument, trade_date
        )
    except Exception:
        log.error("FVG detection failed for %s %s", instrument, trade_date, exc_info=True)
        fvg_instances = []

    # 3. Detect OBs
    try:
        ob_instances = detection.order_blocks.detect(bars_today, instrument)
    except Exception:
        log.error("OB detection failed for %s %s", instrument, trade_date, exc_info=True)
        ob_instances = []

    # 4. Detect BSL/SSL
    try:
        liq_levels = detection.liquidity_sweeps.detect(bars_today, instrument, trade_date)
    except Exception:
        log.error("Liquidity detection failed for %s %s", instrument, trade_date, exc_info=True)
        liq_levels = []

    # 5. Detect Key Opens
    try:
        key_opens = detection.key_opens.detect(bars_today, instrument, trade_date)
    except Exception:
        log.error("Key opens detection failed for %s %s", instrument, trade_date, exc_info=True)
        key_opens = []

    # 6. Detect Opening Gaps
    prior_day = trade_date - timedelta(days=1)
    bars_prior = fetch_ohlcv(instrument, prior_day.isoformat(), trade_date.isoformat(), db)
    for b in bars_prior:
        if isinstance(b.get("ts"), str):
            dt = datetime.fromisoformat(b["ts"].replace("Z", "+00:00"))
            b["ts"] = dt
            b["timestamp"] = dt
    try:
        ndog = detection.opening_gaps.detect_ndog(bars_today, bars_prior, instrument, trade_date)
    except Exception:
        log.error("Opening gap detection failed for %s %s", instrument, trade_date, exc_info=True)
        ndog = None

    # 7. Detect PO3
    try:
        po3_instances = detection.power_of_3.detect_for_day(
            bars_today, instrument, trade_date, news_flag, has_830_news
        )
    except Exception:
        log.error("PO3 detection failed for %s %s", instrument, trade_date, exc_info=True)
        po3_instances = []

    for inst in po3_instances:
        hod_type, hod_detail = _find_nearest_pd_array(inst.hod, fvg_instances, ob_instances)
        lod_type, lod_detail = _find_nearest_pd_array(inst.lod, fvg_instances, ob_instances)
        inst.pd_array_held_hod = hod_type
        inst.pd_array_held_lod = lod_type
        inst.pd_array_detail_hod = hod_detail
        inst.pd_array_detail_lod = lod_detail

    # 8. Detect Macros
    prior_context = {
        "news_flag": news_flag,
        "preceding_po3_phase": next(
            (p.phase for p in po3_instances if p.window_type == "30m_930"), None
        ),
    }
    try:
        macro_instances = detection.macros.detect(bars_today, instrument, trade_date, prior_context)
    except Exception:
        log.error("Macro detection failed for %s %s", instrument, trade_date, exc_info=True)
        macro_instances = []

    # 9. Detect News Candles
    try:
        news_candle_instances = detection.news_candles.detect(
            bars_today, instrument, trade_date, news_events
        )
    except Exception:
        log.error("News candle detection failed for %s %s", instrument, trade_date, exc_info=True)
        news_candle_instances = []

    return {
        "fvg_instances": _instances_to_dicts(fvg_instances),
        "order_block_instances": _instances_to_dicts(ob_instances),
        "liquidity_levels": _instances_to_dicts(liq_levels),
        "key_opens": _instances_to_dicts(key_opens),
        "opening_gap_instances": _instances_to_dicts([ndog]) if ndog else [],
        "po3_instances": _instances_to_dicts(po3_instances),
        "macro_instances": _instances_to_dicts(macro_instances),
        "news_candle_instances": _instances_to_dicts(news_candle_instances),
    }


def run_nightly_pipeline(cfg: Config, target_date: Optional[date] = None) -> None:
    """Run full nightly pipeline: detection + aggregation for all instruments."""
    db = get_db(cfg)
    trade_date = target_date or date.today() - timedelta(days=1)

    print(f"[pipeline] Starting nightly run for {trade_date.isoformat()}")

    for instrument in INSTRUMENTS:
        try:
            print(f"  [detection] Processing {instrument}...")
            instances = run_detection_day(instrument, trade_date, cfg, db)

            for table, rows in instances.items():
                if rows:
                    delete_old_instances(table, instrument, trade_date, db)
                    insert_many(table, rows, db)
                    print(f"    -> {len(rows)} rows -> {table}")
        except Exception:
            log.error("Detection failed for %s on %s", instrument, trade_date, exc_info=True)
            continue

    print("  [aggregation] Building reports...")
    all_stats = build_all_reports(db, trade_date)

    for stat_row in all_stats:
        report_table = f"report_{stat_row['report_type']}_stats"
        db.table(report_table).insert(stat_row).execute()

    if cfg.upstash_redis_url:
        try:
            import redis
            r = redis.from_url(cfg.upstash_redis_url)
            keys = list(r.scan_iter("report:*"))
            for i in range(0, len(keys), 100):
                r.unlink(*keys[i:i+100])
            print(f"    -> Redis cache invalidated ({len(keys)} keys)")
        except Exception as e:
            print(f"    -> Redis cache invalidation failed: {e}")

    print(f"[pipeline] Completed nightly run for {trade_date.isoformat()}")


def run_gex_pipeline(cfg: Config) -> None:
    """Intraday GEX computation. Runs every 30 min 09:00-16:30 ET on trading days."""
    db = get_db(cfg)
    today = date.today()

    for underlying in ["SPX", "NDX"]:
        snapshot = db.table("options_chain_snapshots") \
            .select("*") \
            .eq("underlying", underlying) \
            .gte("timestamp", today.isoformat()) \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()

        if snapshot.data:
            gex = detection.gex.compute_gex(snapshot.data, underlying, today)
            db.table("gex_levels_daily").insert(vars(gex)).execute()
            print(f"  [gex] {underlying}: call_wall={gex.call_wall_strike}")


def run(cfg: Config, mode: str = "nightly", target_date: Optional[str] = None) -> None:
    """CLI entry point."""
    td = date.fromisoformat(target_date) if target_date else None

    if mode == "gex":
        run_gex_pipeline(cfg)
    elif mode == "detect":
        db = get_db(cfg)
        for instrument in INSTRUMENTS:
            instances = run_detection_day(instrument, td or date.today(), cfg, db)
            for table, rows in instances.items():
                if rows:
                    delete_old_instances(table, instrument, td or date.today(), db)
                    insert_many(table, rows, db)
    else:
        run_nightly_pipeline(cfg, td)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quanta Pipeline")
    parser.add_argument("--mode", choices=["nightly", "gex", "detect"], default="nightly")
    parser.add_argument("--date", type=str, help="Target date YYYY-MM-DD")
    args = parser.parse_args()

    cfg = Config.load()
    run(cfg, mode=args.mode, target_date=args.date)
