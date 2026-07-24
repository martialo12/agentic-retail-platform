import logging

from loguru import logger

from arp.config import Settings
from arp.observability.logging import InterceptHandler, configure_logging


def _capture(level="DEBUG", filter=None):
    """Add a temporary loguru sink that collects Message records."""
    seen = []
    handler_id = logger.add(seen.append, level=level, filter=filter)
    return seen, handler_id


def test_configure_logging_is_idempotent():
    # Two calls must not stack handlers or raise.
    configure_logging(Settings(log_format="console"))
    configure_logging(Settings(log_format="json"))


def test_lowercase_log_level_is_accepted():
    # The container passes LOG_LEVEL=info; loguru's level names are upper-case.
    configure_logging(Settings(log_level="info", log_format="json"))
    configure_logging(Settings(log_level="debug", log_format="console"))


def test_console_format_never_raises_on_missing_context():
    # The format references extra[request_id]/extra[run_id]; a bare log outside any
    # request or run must still render, thanks to the default extras.
    configure_logging(Settings(log_format="console"))
    logger.info("no context bound here")  # would KeyError if defaults were absent


def test_stdlib_logging_is_routed_through_loguru():
    configure_logging(Settings(log_format="console"))
    seen, handler_id = _capture()
    try:
        logging.getLogger("uvicorn.error").warning("via stdlib")
    finally:
        logger.remove(handler_id)
    assert any("via stdlib" in str(m) for m in seen)


def test_intercept_handler_preserves_level():
    seen, handler_id = _capture(level="WARNING")
    root = logging.getLogger()
    previous = root.handlers
    root.handlers = [InterceptHandler()]
    try:
        logging.getLogger().warning("boom")
    finally:
        root.handlers = previous
        logger.remove(handler_id)
    assert any(m.record["level"].name == "WARNING" for m in seen)
