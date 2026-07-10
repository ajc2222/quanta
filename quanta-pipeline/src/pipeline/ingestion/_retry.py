"""Shared retry configuration for all ingestion modules."""

import logging

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger("pipeline.ingestion")

# Retry on transient network errors + HTTP 429/503
TRANSIENT = (
    requests.ConnectionError,
    requests.Timeout,
    ConnectionResetError,
    TimeoutError,
)


def is_transient_http(exc: BaseException) -> bool:
    if isinstance(exc, requests.HTTPError):
        return exc.response is not None and exc.response.status_code in (429, 502, 503, 504)
    return False


def http_retry(label: str = ""):
    """Decorator factory: exponential backoff, max 3 attempts, log on retry."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type(TRANSIENT) | retry_if_exception(is_transient_http),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,
    )
