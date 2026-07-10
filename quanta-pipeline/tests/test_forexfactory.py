"""Tests for the ForexFactory ingestion module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.pipeline.config import Config
from src.pipeline.ingestion.forexfactory_ingest import (
    _fetch_json,
    _parse_json_event,
    _fetch_html,
    run,
)


@pytest.fixture
def cfg() -> Config:
    return Config(
        databento_api_key="test_key",
        supabase_database_url="postgresql://test:test@localhost:6543/test",
    )


SAMPLE_JSON = [
    {
        "date": "2026-07-09",
        "time": "08:30",
        "country": "USD",
        "impact": "3",
        "title": "CPI MoM",
        "actual": "0.2%",
        "forecast": "0.3%",
        "previous": "0.1%",
    },
    {
        "date": "2026-07-09",
        "time": "10:00",
        "country": "EUR",
        "impact": "2",
        "title": "German ZEW",
        "actual": "",
        "forecast": "15.2",
        "previous": "14.8",
    },
]


def test_parse_json_event():
    event = _parse_json_event(SAMPLE_JSON[0])
    assert event is not None
    assert event["currency"] == "USD"
    assert event["impact"] == "High"
    assert event["event"] == "CPI MoM"
    assert event["actual"] == "0.2%"


def test_parse_json_event_missing_date():
    event = _parse_json_event({"impact": "1"})
    assert event is None


def test_fetch_json_success():
    with patch("src.pipeline.ingestion.forexfactory_ingest.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = SAMPLE_JSON

        data = _fetch_json()
        assert len(data) == 2
        assert data[0]["title"] == "CPI MoM"


def test_fetch_json_retries_on_failure():
    with patch("src.pipeline.ingestion.forexfactory_ingest.requests.get") as mock_get:
        mock_get.side_effect = ConnectionError("no network")

        with pytest.raises(ConnectionError):
            _fetch_json()
        assert mock_get.call_count == 3


SAMPLE_HTML = """
<html><body>
<table class="calendar_table">
<tr class="calendar_row">
    <td>Wed Jul 9</td>
    <td>08:30</td>
    <td>USD</td>
    <td></td>
    <td data-img_url="icon_red.gif"></td>
    <td>CPI MoM</td>
    <td>0.2%</td>
    <td>0.3%</td>
    <td>0.1%</td>
</tr>
</table>
</body></html>
"""


def test_fetch_html_parse():
    with patch("src.pipeline.ingestion.forexfactory_ingest.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = SAMPLE_HTML

        events = _fetch_html()
        assert len(events) >= 1
        assert events[0]["currency"] == "USD"
        assert events[0]["impact"] == "High"
        assert events[0]["event"] == "CPI MoM"


def test_run_json_success(cfg):
    with (
        patch("src.pipeline.ingestion.forexfactory_ingest._fetch_json", return_value=SAMPLE_JSON),
        patch("src.pipeline.ingestion.forexfactory_ingest.upsert_news_events", return_value=2) as mock_upsert,
    ):
        result = run(cfg)
        assert result == 2
        mock_upsert.assert_called_once()


def test_run_fallback_to_html(cfg):
    with (
        patch("src.pipeline.ingestion.forexfactory_ingest._fetch_json", side_effect=ValueError("JSON down")),
        patch("src.pipeline.ingestion.forexfactory_ingest._fetch_html", return_value=[{"date": "2026-07-09", "time_et": "08:30", "currency": "USD", "impact": "High", "event": "CPI", "actual": None, "forecast": None, "previous": None}]),
        patch("src.pipeline.ingestion.forexfactory_ingest.upsert_news_events", return_value=1),
    ):
        result = run(cfg)
        assert result == 1
