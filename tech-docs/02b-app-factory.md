# Phase 02b — App Factory & Middleware

## Goal

Stand up `create_app()` so router registration, CORS, request-ID
correlation, global error handling, and the dev `/static` mount all live in
one place. Endpoint phases (06, 07) plug into this factory.

## Prerequisites

- Phase 02a merged: `Settings` and `get_settings` exist.

## Deliverables

`backend/app/main.py` exposes `create_app()` and a module-level `app`
instance.

Responsibilities, in order:

1. **Router registration.** `health` (phase 02f) is registered now;
   `verify` (phase 06) and `nearby` (phase 07) get registered as their
   modules land. No premature imports — registration is explicit.
2. **CORS.** Allow the Flutter Web dev origin (`http://localhost:*`) in
   dev only; production origins come from settings. Do not use `"*"` —
   credentials-bearing requests will silently fail.
3. **Request-ID middleware.** Read `X-Request-ID` from the client; if
   absent, generate `uuid4().hex`. Echo on every response and inject into
   the structlog context (phase 02g consumes it).
4. **Global exception handler.** Any unhandled exception becomes
   `500 Internal Server Error` with a JSON body
   `{"detail": "internal error", "request_id": "<id>"}`. **Never** leak
   stack traces or framework internals to the client.
5. **`/static` mount.** Serve `settings.upload_dir` at `/static` for dev
   only. Production uses a CDN/object store; gate the mount behind an
   env flag.

## Acceptance criteria

- [ ] `uvicorn backend.app.main:app --reload` boots cleanly with no
      warnings about missing env vars (after copying `.env.example`).
- [ ] A client that sends `X-Request-ID: abc123` sees the same value back
      in the response header.
- [ ] A client that sends no `X-Request-ID` gets a generated one in the
      response.
- [ ] Forcing an unhandled exception in a test route returns `500` with
      `request_id` in the body and no traceback in the response.
- [ ] CORS preflight from `http://localhost:5173` succeeds in dev.

## Pitfalls / notes

- Register the request-ID middleware **before** any logging middleware so
  every log line for a request can carry the ID.
- The `/static` mount is dev-only. Forgetting to gate it in prod leaks
  the upload directory listing if directory listing is ever enabled by a
  reverse proxy.
- Don't catch `HTTPException` in the global handler — FastAPI already
  formats those. The global handler is the last-resort net for everything
  else.
