"""Ingest economic calendar events from ForexFactory.

Primary source: the free JSON endpoint at
  https://nfs.faireconomy.media/ff_calendar_thisweek.json

Falls back to scraping the HTML calendar page if the JSON endpoint is
unavailable.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pytz
import requests
from bs4 import BeautifulSoup

from ..config import Config
from ..db import upsert_news_events
from ._retry import http_retry

log = logging.getLogger("pipeline.ingestion.forexfactory")

FF_JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FF_HTML_URL = "https://www.forexfactory.com/calendar"

IMPACT_MAP = {
    "3": "High",
    "2": "Medium",
    "1": "Low",
}

ET = pytz.timezone("America/New_York")


# ---------------------------------------------------------------------------
# JSON source (primary)
# ---------------------------------------------------------------------------


@http_retry("forexfactory-json")
def _fetch_json() -> list[dict]:
    resp = requests.get(FF_JSON_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _parse_json_event(raw: dict) -> dict[str, Any] | None:
    """Map a JSON event dict to our schema."""
    try:
        event_date = date.fromisoformat(raw["date"])
    except (KeyError, ValueError):
        return None

    return {
        "date": event_date,
        "time_et": raw.get("time"),
        "currency": raw.get("country", ""),
        "impact": IMPACT_MAP.get(raw.get("impact", ""), "Low"),
        "event": raw.get("title", ""),
        "actual": raw.get("actual"),
        "forecast": raw.get("forecast"),
        "previous": raw.get("previous"),
    }


# ---------------------------------------------------------------------------
# HTML scrape fallback
# ---------------------------------------------------------------------------


@http_retry("forexfactory-html")
def _fetch_html() -> list[dict]:
    resp = requests.get(FF_HTML_URL, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rows: list[dict] = []
    for tr in soup.select("table.calendar_table tr.calendar_row"):
        cells = tr.select("td")
        if len(cells) < 8:
            continue

        cell_date = cells[0].get_text(strip=True)
        cell_time = cells[1].get_text(strip=True)
        cell_currency = cells[2].get_text(strip=True)
        cell_impact = cells[4].get("data-img_url", "")
        cell_event = cells[5].get_text(strip=True)
        cell_actual = cells[6].get_text(strip=True)
        cell_forecast = cells[7].get_text(strip=True)
        cell_previous = cells[8].get_text(strip=True)

        # Parse date — FF shows "Wed Jul 9" or similar relative
        try:
            parsed_date = datetime.strptime(cell_date, "%a %b %d").replace(year=datetime.now().year)
        except ValueError:
            continue

        # Map impact icon filename to level
        if "red" in cell_impact:
            impact = "High"
        elif "orange" in cell_impact:
            impact = "Medium"
        else:
            impact = "Low"

        rows.append({
            "date": parsed_date.date(),
            "time_et": cell_time,
            "currency": cell_currency,
            "impact": impact,
            "event": cell_event,
            "actual": cell_actual or None,
            "forecast": cell_forecast or None,
            "previous": cell_previous or None,
        })

    return rows


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(cfg: Config) -> int:
    """Fetch and upsert ForexFactory events for this and next week.

    Returns number of events upserted.
    """
    log.info("ForexFactory: fetching calendar")

    try:
        raw = _fetch_json()
        events = [_parse_json_event(e) for e in raw]
        events = [e for e in events if e is not None]
        source = "json"
    except Exception:
        log.warning("ForexFactory JSON failed, falling back to HTML scrape", exc_info=True)
        try:
            events = _fetch_html()
            source = "html"
        except Exception:
            log.exception("ForexFactory HTML scrape also failed")
            return 0

    if not events:
        log.warning("ForexFactory: no events parsed from %s", source)
        return 0

    inserted = upsert_news_events(events)
    log.info("ForexFactory: upserted %d events (%s)", inserted, source)
    return inserted
