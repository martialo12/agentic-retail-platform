"""One logging pipeline for the whole process (application + uvicorn + stdlib).

Everything is emitted to **stdout** — never a file. In a container the platform
(Cloud Run / GKE) captures stdout into its log system; writing files on a
read-only or ephemeral filesystem is both fragile and pointless. `json` format
makes every field queryable there; `console` stays readable on a laptop.

The single seam is `configure_logging()`, called once at process start.
"""

from __future__ import annotations

import logging
import sys

from loguru import logger

from arp.config import Settings, get_settings

# Placeholders so a format string referencing these never raises before a
# request or a run has bound its real value.
_DEFAULT_EXTRA = {"request_id": "-", "run_id": "-"}

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <7}</level> | "
    "<cyan>req={extra[request_id]}</cyan> <magenta>run={extra[run_id]}</magenta> | "
    "<level>{message}</level>"
)

# stdlib loggers whose records must flow through loguru rather than their own
# handlers, so uvicorn's access/error lines share one format and one sink.
_STDLIB_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "gunicorn",
    "gunicorn.error",
    "fastapi",
)


class InterceptHandler(logging.Handler):
    """Route a stdlib `LogRecord` into loguru, preserving level and call site."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Walk out of the logging machinery so loguru reports the real caller.
        frame, depth = logging.currentframe(), 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(settings: Settings | None = None) -> None:
    """Install the single stdout sink and make stdlib logging flow through it.

    Idempotent: re-running replaces the handlers rather than stacking them.
    """
    settings = settings or get_settings()
    # loguru level names are upper-case; accept any casing from the environment.
    level = settings.log_level.upper()

    if settings.log_format == "json":
        handler = {
            "sink": sys.stdout,
            "level": level,
            "serialize": True,
            "enqueue": True,
            "backtrace": settings.log_diagnose,
            "diagnose": settings.log_diagnose,
        }
    else:
        handler = {
            "sink": sys.stdout,
            "level": level,
            "format": _CONSOLE_FORMAT,
            "enqueue": True,
            "backtrace": settings.log_diagnose,
            "diagnose": settings.log_diagnose,
        }

    logger.configure(handlers=[handler], extra=dict(_DEFAULT_EXTRA))

    # `force=True` drops any handler a library installed on the root logger.
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in _STDLIB_LOGGERS:
        stdlib_logger = logging.getLogger(name)
        stdlib_logger.handlers = [InterceptHandler()]
        stdlib_logger.propagate = False
