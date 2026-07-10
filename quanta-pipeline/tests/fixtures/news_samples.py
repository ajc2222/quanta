"""Synthetic news event stubs for tests."""

from datetime import datetime


def sample_news_events() -> list[dict]:
    return [
        {"event_name": "CPI MoM", "event_time": datetime(2026, 7, 8, 8, 30),
         "impact": "high", "currency": "USD"},
        {"event_name": "Jobless Claims", "event_time": datetime(2026, 7, 8, 8, 30),
         "impact": "medium", "currency": "USD"},
    ]
