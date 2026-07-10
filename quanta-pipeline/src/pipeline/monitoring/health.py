"""Minimal HTTP health-check server.

Railway polls the configured port; we also surface a /ready endpoint
that reports the last run status of each ingestion module.
"""

from __future__ import annotations

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Any

log = logging.getLogger("pipeline.monitoring.health")


class _Handler(BaseHTTPRequestHandler):
    status_store: dict[str, Any] = {}  # shared across instances

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "service": "quanta-pipeline"})
        elif self.path == "/ready":
            self._respond(200, self.status_store)
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, body: dict) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # silence health-check noise


def serve(port: int, status_store: dict[str, Any]) -> HTTPServer:
    _Handler.status_store = status_store
    server = HTTPServer(("0.0.0.0", port), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("Health server listening on :%d", port)
    return server
