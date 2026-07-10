"""Thin Postgres access via supabase client for detection/aggregation pipeline.

Separate from the ingestion pipeline's psycopg2-based db.py.
"""

from datetime import date
from typing import Any

from supabase import create_client, Client
from src.config import Config


_db: Client | None = None


def get_db(cfg: Config) -> Client:
    global _db
    if _db is None:
        _db = create_client(cfg.supabase_url, cfg.supabase_key)
    return _db


def insert_many(table: str, rows: list[dict], db: Client) -> None:
    """Batch insert rows. Each row dict keys match column names."""
    if not rows:
        return
    db.table(table).insert(rows).execute()


def delete_old_instances(table: str, instrument: str, cutoff_date: date, db: Client) -> None:
    """Remove stale instances before reprocessing a date range."""
    db.table(table).delete().eq("instrument", instrument).gte(
        "date", cutoff_date.isoformat()
    ).execute()


def fetch_ohlcv(
    instrument: str, start: str, end: str, db: Client, timeframe: str = "1m"
) -> list[dict]:
    """Fetch OHLCV bars for a date range. Returns list of dicts keyed by column."""
    resp = db.table("ohlcv_1m") \
        .select("*") \
        .eq("instrument", instrument) \
        .gte("ts", start) \
        .lte("ts", end) \
        .order("ts") \
        .execute()
    return resp.data
