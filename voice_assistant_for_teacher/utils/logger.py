"""Consistent logger factory used across every module in the project."""

from __future__ import annotations

import logging
import sys
from functools import lru_cache

from config.settings import settings

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%H:%M:%S"


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """Return a configured logger, memoized per-name so handlers are
    attached exactly once even if this is called many times (e.g. on every
    Streamlit rerun)."""
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level.upper())

    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
        logger.addHandler(handler)
        logger.propagate = False

    return logger
