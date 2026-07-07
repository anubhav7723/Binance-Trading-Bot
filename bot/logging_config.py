"""
Centralized logging configuration.

Logs go to both the console (INFO+) and a rotating log file (DEBUG+),
so the file captures full request/response detail while the console
stays readable.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return the root 'trading_bot' logger.

    Idempotent: calling this multiple times will not add duplicate handlers.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(level)

    if logger.handlers:
        # Already configured (e.g. re-imported in tests) — don't duplicate handlers.
        return logger

    formatter = logging.Formatter(_LOG_FORMAT)

    # Rotating file handler: keeps logs from growing unbounded.
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler: only warnings/errors/info-level summaries, keeps CLI clean.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
