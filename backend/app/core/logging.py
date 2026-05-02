"""Structured logging setup.

Every log record is annotated with the active request ID (or '-' outside
a request). The formatter emits a single line of structured-ish text
suitable for ``grep``-friendly local development; production deployments
can swap this for a JSON formatter via env config.
"""

from __future__ import annotations

import logging

from app.core.middleware import get_request_id


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    fmt = "%(asctime)s [%(levelname)s] [rid=%(request_id)s] %(name)s: %(message)s"
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    handler.addFilter(_RequestIdFilter())

    root = logging.getLogger()
    # Replace any existing handlers so the request-id filter is always applied.
    root.handlers = [handler]
    root.setLevel(level)
