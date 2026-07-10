"""Generic aggregation engine. Pure pandas - instance rows in, stat rows out.

One aggregate() function parameterized by MetricDef lists covering
slicing by weekday, session, news flag, HTF phase, etc.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Optional

import pandas as pd
from supabase import Client


@dataclass
class MetricDef:
    """Definition of a single aggregated metric."""
    name: str
    column: str
    agg_func: str | Callable
    group_by: list[str]
    filters: Optional[dict[str, Any]] = None
    output_type: str = "avg"


@dataclass
class AggregationResult:
    """Aggregation output row."""
    report_type: str = ""
    instrument: str = ""
    lookback_days: int = 0
    slice_key: str = ""
    metric_name: str = ""
    value: float = 0.0
    sample_size: int = 0
    computed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.computed_at is None:
            self.computed_at = datetime.now(timezone.utc)


def fetch_instances(
    db: Client, table: str, instrument: str,
    start_date: date, end_date: date
) -> pd.DataFrame:
    """Fetch instance rows as a pandas DataFrame."""
    resp = db.table(table) \
        .select("*") \
        .eq("instrument", instrument) \
        .gte("date", start_date.isoformat()) \
        .lte("date", end_date.isoformat()) \
        .execute()

    if not resp.data:
        return pd.DataFrame()

    df = pd.DataFrame(resp.data)

    for col in ("date", "creation_time", "fill_time"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    return df


def _safe(val: float, default: float = 0.0) -> float:
    """Replace NaN/Inf with default (Postgres rejects non-finite floats)."""
    return default if (val != val or val == float("inf") or val == float("-inf")) else val


def compute_rates(df: pd.DataFrame, value_col: str, group_cols: list[str]) -> list[AggregationResult]:
    """Compute rate (0-1) of True/1 values in value_col, grouped by group_cols."""
    if df.empty or value_col not in df.columns:
        return []

    results: list[AggregationResult] = []
    df.loc[:, value_col] = df[value_col].astype(bool).astype(float)
    grouped = df.groupby(group_cols)[value_col]

    for name, group in grouped:
        rate = group.mean()
        n = len(group)
        if isinstance(name, tuple):
            slice_key = ";".join(f"{g}={v}" for g, v in zip(group_cols, name))
        else:
            slice_key = f"{group_cols[0]}={name}"

        results.append(AggregationResult(
            slice_key=slice_key, metric_name=f"{value_col}_rate",
            value=_safe(float(rate)), sample_size=n,
        ))

    return results


def compute_averages(df: pd.DataFrame, value_col: str, group_cols: list[str]) -> list[AggregationResult]:
    """Compute mean of value_col grouped by group_cols."""
    if df.empty or value_col not in df.columns:
        return []

    results: list[AggregationResult] = []
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    grouped = df.groupby(group_cols)[value_col]

    for name, group in grouped:
        avg = group.mean()
        n = group.count()
        if isinstance(name, tuple):
            slice_key = ";".join(f"{g}={v}" for g, v in zip(group_cols, name))
        else:
            slice_key = f"{group_cols[0]}={name}"

        results.append(AggregationResult(
            slice_key=slice_key, metric_name=f"avg_{value_col}",
            value=_safe(float(avg)), sample_size=int(n),
        ))

    return results


def compute_distributions(df: pd.DataFrame, value_col: str, bucket_fn: Optional[Callable] = None) -> list[AggregationResult]:
    """Compute distribution of value_col values into buckets."""
    if df.empty or value_col not in df.columns:
        return []

    results: list[AggregationResult] = []
    values = pd.to_numeric(df[value_col], errors="coerce").dropna()

    if bucket_fn:
        buckets = values.apply(bucket_fn)
        dist = buckets.value_counts(normalize=True)
        for bucket, pct in dist.items():
            results.append(AggregationResult(
                slice_key=f"bucket={bucket}",
                metric_name=f"dist_{value_col}",
                value=_safe(float(pct)), sample_size=int(len(values)),
            ))
    return results


def aggregate_all(
    report_type: str, instrument: str, lookback_days: int,
    df: pd.DataFrame, metric_defs: list[MetricDef],
) -> list[AggregationResult]:
    """Run all metric definitions against a dataframe and return flat results."""
    if df.empty:
        return []

    results: list[AggregationResult] = []

    for md in metric_defs:
        filtered = df
        if md.filters:
            for col, val in md.filters.items():
                if col in filtered.columns:
                    filtered = filtered[filtered[col] == val]

        if filtered.empty:
            continue

        if md.agg_func in ("mean", "avg"):
            results.extend(compute_averages(filtered, md.column, md.group_by))
        elif md.agg_func == "rate":
            results.extend(compute_rates(filtered, md.column, md.group_by))
        elif md.agg_func == "distribution":
            results.extend(compute_distributions(filtered, md.column, None))

    for r in results:
        r.report_type = report_type
        r.instrument = instrument
        r.lookback_days = lookback_days

    return results


# --- Report-specific metric definitions ------------------------------------

FVG_METRICS = [
    MetricDef("fill_rate", "status", "rate", group_by=["weekday"], filters={"status": "filled"}),
    MetricDef("fill_rate_by_tf", "status", "rate", group_by=["timeframe"]),
    MetricDef("avg_fill_time", "fill_pct", "mean", group_by=["timeframe"]),
]

OB_METRICS = [
    MetricDef("respect_rate", "outcome", "rate", group_by=["timeframe"], filters={"outcome": "respected"}),
    MetricDef("break_rate", "outcome", "rate", group_by=["timeframe"], filters={"outcome": "broken"}),
    MetricDef("avg_test_time", "first_test_time", "mean", group_by=["timeframe"]),
]

PO3_METRICS = [
    MetricDef("bullish_rate", "phase", "rate", group_by=["weekday"], filters={"phase": "bullish"}),
    MetricDef("bearish_rate", "phase", "rate", group_by=["weekday"], filters={"phase": "bearish"}),
    MetricDef("ambiguous_rate", "phase", "rate", group_by=["weekday"], filters={"phase": "unconfirmed"}),
    MetricDef("avg_range", "close", "mean", group_by=["window_type"]),
    MetricDef("hod_time_distribution", "hod_time", "distribution", group_by=["window_type"]),
    MetricDef("lod_time_distribution", "lod_time", "distribution", group_by=["window_type"]),
    MetricDef("pd_array_hod_dist", "pd_array_held_hod", "distribution", group_by=[]),
    MetricDef("pd_array_lod_dist", "pd_array_held_lod", "distribution", group_by=[]),
]

LIQUIDITY_METRICS = [
    MetricDef("sweep_rate", "swept", "rate", group_by=["level_type"]),
    MetricDef("reversal_rate_after_sweep", "post_sweep_direction", "rate",
              group_by=["level_type"], filters={"swept": True}),
]

KEYOPEN_METRICS = [
    MetricDef("respect_rate", "respected", "rate", group_by=["open_type"]),
    MetricDef("rejection_rate", "rejection", "rate", group_by=["open_type"]),
    MetricDef("avg_time_to_test", "time_to_test", "mean", group_by=["open_type"]),
    MetricDef("avg_deviation", "deviation_before_test_pts", "mean", group_by=["open_type"]),
]

NEWS_CANDLE_METRICS = [
    MetricDef("high_taken_rate", "high_taken", "rate", group_by=["event_name"]),
    MetricDef("low_taken_rate", "low_taken", "rate", group_by=["event_name"]),
    MetricDef("both_sides_rate", "high_taken", "rate", group_by=[], filters={"high_taken": True, "low_taken": True}),
    MetricDef("avg_post_take_magnitude", "post_take_magnitude_pts", "mean", group_by=["impact"]),
]

MACRO_METRICS = [
    MetricDef("bullish_rate", "direction", "rate", group_by=["window_type"], filters={"direction": "bullish"}),
    MetricDef("bearish_rate", "direction", "rate", group_by=["window_type"], filters={"direction": "bearish"}),
    MetricDef("choppy_rate", "direction", "rate", group_by=["window_type"], filters={"direction": "choppy"}),
    MetricDef("avg_magnitude", "magnitude_pts", "mean", group_by=["window_type"]),
]

OPENING_GAP_METRICS = [
    MetricDef("fill_rate", "fill_status", "rate", group_by=["gap_type"], filters={"fill_status": "filled"}),
    MetricDef("avg_fill_time", "fill_pct", "mean", group_by=["gap_type"]),
    MetricDef("fill_rate_by_weekday", "fill_status", "rate", group_by=["gap_type", "weekday"]),
]

GEX_METRICS = [
    MetricDef("call_wall_respect_rate", "call_wall_strike", "mean", group_by=["underlying"]),
    MetricDef("put_wall_respect_rate", "put_wall_strike", "mean", group_by=["underlying"]),
]


def build_report(
    report_type: str, instrument: str, lookback_days: int,
    instance_table: str, metrics: list[MetricDef],
    db: Client, end_date: Optional[date] = None,
) -> list[AggregationResult]:
    """End-to-end: fetch -> aggregate -> stamp with metadata."""
    end = end_date or date.today()
    start = end - timedelta(days=lookback_days * 7 // 5 + 5)

    df = fetch_instances(db, instance_table, instrument, start, end)

    if not df.empty and "date" in df.columns:
        df["weekday"] = df["date"].dt.dayofweek.map({
            0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri",
        })
    if not df.empty and "high" in df.columns and "low" in df.columns:
        df["high_low_range"] = pd.to_numeric(df["high"], errors="coerce") - pd.to_numeric(df["low"], errors="coerce")

    return aggregate_all(report_type, instrument, lookback_days, df, metrics)
