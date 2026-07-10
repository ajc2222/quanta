"""Structured JSON logging to stdout — Railway-native format."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger("pipeline")
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(handler)
