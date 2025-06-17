# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# filename: logging_config.py
# author: dunamismax
# version: 1.0.0
# date: 06-17-2025
# github: https://github.com/dunamismax
# description: Configures structured logging for the application using structlog.
# -----------------------------------------------------------------------------
import logging
import sys

import structlog


def setup_logging(log_level: str = "INFO") -> None:
    """
    Set up structured logging for the entire application.

    This configuration sets up structlog to process all logs from Python's
    standard logging library, ensuring consistent, structured output in
    JSON format.

    Args:
        log_level: The minimum log level to capture (e.g., "INFO", "DEBUG").
    """
    log_level_upper = log_level.upper()
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level_upper)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
