# Phase 07b — HTTP Cache Headers

## Goal

A user panning the map a few pixels should not re-hit the database for
each frame. A short `Cache-Control` header lets the browser and any
intermediate cache hold the response for 15 seconds.

## Prerequisites

- Phase 07a merged.

## Deliverables

```python
@router.get("/contributions/nearby", response_model=NearbyResponse)
async def nearby(
    response: Response,
    latitude: float = Query(...),
    # ... other params
) -> NearbyResponse:
    rows = await find_nearby(...)
    response.headers["Cache-Control"] = "public, max-age=15"
    return NearbyResponse(items=[_to_pin(r) for r in rows])
```

The `15s` budget:

- Long enough that a user dragging the map 50 px/sec doesn't re-fetch
  on every interaction.
- Short enough that a freshly contributed pin shows up within ~15s for
  another user nearby.
- No server-side cache (Redis, in-process). The GIST index plus
  Postgres' buffer cache handles MVP traffic. Revisit only if profiling
  proves it isn't enough.

## Acceptance criteria

- [ ] Every `200` response from `/contributions/nearby` has
      `Cache-Control: public, max-age=15`.
- [ ] An empty result (`items: []`) also has the header — clients
      cache "no pins here" too.
- [ ] Error responses (`422`) do not have a long `Cache-Control` —
      validation errors should not be cached. FastAPI's default for
      error bodies is fine; do not add the header on the error path.

## Pitfalls / notes

- **`public` matters.** Without it, intermediate caches (CDN, corporate
  proxy) won't cache the response even if the client would.
- **Don't bump to `max-age=60` for "free perf."** Pins should appear
  promptly for users near a fresh contribution; a longer TTL turns a
  feature into a bug.
- **Don't add `ETag`** here. The endpoint's response varies on four
  query params and a database that mutates; an `ETag` strategy that
  actually validates is more complex than the perf upside justifies for
  MVP.
- **Vary headers** are not needed — there's no auth, no
  content-negotiation, and the response is keyed only by query string.
