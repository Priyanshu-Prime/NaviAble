# Phase 07d — CORS & Public Access

## Goal

`/contributions/nearby` is read-only and stays unauthenticated in MVP.
The Flutter Web origin is allowed via the CORS middleware from phase
02b. Authenticated personalisation goes on a separate prefix later.

## Prerequisites

- Phase 02b merged: CORS middleware configured in `create_app`.
- Phase 07a merged: endpoint exists.

## Deliverables

### No new code in this phase

The endpoint inherits CORS from the app-level middleware. No
endpoint-specific CORS handling, no `OPTIONS` route, no auth dependency.

### Documented decision

> **Discovery is anonymous.** Map tiles must load for any visitor,
> including users who haven't signed up. Adding auth here would gate
> the platform's primary value — seeing accessibility data near you —
> behind a sign-up wall.
>
> Future authenticated features ("places I contributed to," "places
> I've saved," "report this pin") get a new prefix:
> `/api/v1/me/contributions`, `/api/v1/me/saved`. **Do not bolt auth
> onto `/contributions/nearby`** — its current callers don't expect it,
> and the endpoint's caching characteristics depend on
> non-personalised responses.

### Rate limiting (light touch)

In MVP, no per-IP rate limiting at the application level. Reverse
proxy / CDN handles abuse. If application-level limits become
necessary:

- Token bucket keyed by IP, applied via FastAPI middleware.
- Limit ~60 requests/min per IP. Map dragging shouldn't approach this.
- Apply only to discovery endpoints; never to `/healthz`.

## Acceptance criteria

- [ ] A request from `http://localhost:5173` (Flutter Web dev) succeeds
      with the expected CORS headers.
- [ ] An `OPTIONS` preflight to `/contributions/nearby` returns
      `204` with `Access-Control-Allow-*` headers.
- [ ] No auth dependency is attached to the route.
- [ ] No `Authorization` header is required or inspected.

## Pitfalls / notes

- **Don't use `allow_origins=["*"]` with `allow_credentials=True`.** The
  combination is invalid CORS and modern browsers reject the response.
  Allow specific origins, or origins without credentials.
- **`Vary: Origin`** is added automatically by `CORSMiddleware`. Don't
  remove it — it tells caches to differentiate per origin.
- The "no auth" decision is intentional. If a future requirement
  changes this (e.g. compliance), the right move is to add auth to a
  new endpoint at a new path, not to mutate this one.
