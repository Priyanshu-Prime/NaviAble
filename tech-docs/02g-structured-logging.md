# Phase 02g — Structured Logging

## Goal

Every log line is JSON, every line carries `request_id`, and there are no
`print()` calls in committed code. Logs are readable by humans during
local dev and parseable by log aggregators in prod.

## Prerequisites

- Phase 02b merged: request-ID middleware injects the ID into context.

## Deliverables

Use `structlog` (preferred) or stdlib `logging` with a JSON formatter.

`backend/app/core/logging.py`:

```python
def configure_logging(*, level: str = "INFO", json: bool = True) -> None:
    """Wire structlog so every log line:
       - carries `request_id` from contextvars (set by middleware),
       - renders as JSON in prod, key-value in dev,
       - includes timestamp, logger name, level."""
```

The request-ID middleware from phase 02b pushes the ID into a
`contextvars.ContextVar`; structlog's `merge_contextvars` processor pulls
it onto every log line automatically.

Module loggers:

```python
log = structlog.get_logger(__name__)
log.info("verify.received", review_len=len(review), lat=lat, lon=lon)
```

Use **event names**, not f-strings. `"verify.received"` is greppable;
`"got a verify request with lat=12.97 lon=77.59"` is not.

## Acceptance criteria

- [ ] A request with `X-Request-ID: abc123` produces log lines that all
      contain `"request_id": "abc123"`.
- [ ] Log output in prod mode is valid JSON, line-delimited.
- [ ] `grep -r 'print(' backend/app` returns no matches.
- [ ] Switching `LOG_JSON=false` in dev produces human-readable output
      without restarting changing any other code.
- [ ] Uncaught exceptions are logged with traceback and `request_id`,
      then re-raised to the global handler from phase 02b.

## Pitfalls / notes

- `contextvars` is async-safe; thread-local storage is not. Do not use
  `threading.local` for request ID — `to_thread` workers won't see it.
- structlog's processor order matters: `merge_contextvars` must come
  before the renderer. Get it wrong and `request_id` is silently dropped.
- Don't log full request bodies. Log lengths and shapes; a 2 KB review
  in every log line bloats storage and risks PII.
