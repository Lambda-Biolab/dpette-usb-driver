"""Centralised logging configuration for the dpette package."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_CONFIGURED: set[str] = set()

LOG_DIR = Path(__file__).resolve().parents[2] / "captures"
"""Default directory for session log files."""


def get_logger(
    name: str,
    *,
    level: int = logging.DEBUG,
    log_to_file: bool = False,
) -> logging.Logger:
    """Return a logger with consistent formatting.

    Calling this multiple times with the same *name* is safe — handlers
    are added only once.

    Parameters
    ----------
    name:
        Logger name, typically ``__name__``.
    level:
        Minimum log level.
    log_to_file:
        If ``True``, also write to ``captures/session.log``.
    """
    logger = logging.getLogger(name)

    if name in _CONFIGURED:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(LOG_DIR / "session.log")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    _CONFIGURED.add(name)
    return logger
