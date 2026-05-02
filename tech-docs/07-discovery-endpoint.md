# Phase 07 — `GET /api/v1/contributions/nearby`

## Goal

Expose the spatial query that the map view (phase 10) calls when the user
pans, zooms, or shares their location. Given a lat/lon and a radius in
metres, return contributions ordered by distance, filtered to display-safe
statuses (`PUBLIC` and optionally `CAVEAT`), and bounded by a sensible
result cap.

## Prerequisites

- Phase 01 merged: `find_nearby` exists in `db/queries.py`.
- Phase 02 merged: `NearbyQuery`, `NearbyResponse`, `ContributionPin`
  schemas defined.

## Spec

| Field          | Value                                                |
|----------------|------------------------------------------------------|
| Method + path  | `GET /api/v1/contributions/nearby`                   |
| Query params   | `latitude`, `longitude`, `radius_m`, `include_caveat` |
| Response       | `NearbyResponse { items: ContributionPin[] }`        |
| Status filter  | Always exclude `HIDDEN`. Include `CAVEAT` per flag.  |
| Default radius | None — caller must specify (no surprises)            |
| Max radius     | `10 000 m` (10 km) — bigger queries hit a cap        |
| Max results    | `200` rows                                           |

## Current state

`find_nearby` exists from phase 01 but no router exposes it yet.

## Deliverables

### 1. The endpoint

`backend/app/api/routers/nearby.py`:

```python
router = APIRouter(prefix="/api/v1", tags=["discovery"])

@router.get("/contributions/nearby", response_model=NearbyResponse)
async def nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(..., gt=0, le=10_000),
    include_caveat: bool = Query(True),
    session: AsyncSession = Depends(get_session),
) -> NearbyResponse:
    rows = await find_nearby(
        session,
        lat=latitude, lon=longitude, radius_m=radius_m,
        include_caveat=include_caveat, limit=200,
    )
    return NearbyResponse(items=[_to_pin(r) for r in rows])
```

Keep `_to_pin` as a small helper in the same file. It maps a
`Contribution` ORM object to the `ContributionPin` API shape, including
stripping the location geometry into separate `latitude` / `longitude`
floats so the frontend does not have to parse WKB.

### 2. Caching

Discovery responses are cacheable for short windows. Add an HTTP cache
header:

```python
response.headers["Cache-Control"] = "public, max-age=15"
```

15 seconds is short enough to stay fresh but long enough that a user
panning the map a few pixels does not re-hit the database. Do not add a
server-side cache (Redis etc.) in this phase — the GIST index plus
Postgres's own buffer cache is plenty for MVP. Revisit only if profiling
shows it's needed.

### 3. Pagination (deferred)

200 rows per response is a hard cap. If the cap is regularly hit in
practice, paginate by distance (cursor = last-distance) in a follow-up
phase. Document the decision here so it is not silently re-done as
offset-based pagination, which is the wrong shape for spatial queries.

### 4. CORS / public access

This endpoint is read-only and may eventually be public — accessible
without auth so that map tiles can load anonymously. CORS for the
Flutter Web origin is set in phase 02. No additional auth gate here in
the MVP.

If the project ever adds authenticated personalisation ("places I
contributed to," "places I've saved"), those become separate endpoints
under a different prefix. Do not bolt auth onto `/nearby` — keep it
unauthenticated and cheap.

### 5. Image URL handling

`ContributionPin.image_url` should be a fully-qualified URL the frontend
can render directly. In dev, that is something like
`http://localhost:8000/static/<uuid>.jpg`. In prod, it is a CDN URL.
Compose it from `settings.public_base_url + settings.static_prefix +
image_path.name`. **Don't** return the absolute filesystem path.

## Acceptance criteria

- [ ] `GET /api/v1/contributions/nearby?latitude=12.97&longitude=77.59&radius_m=500`
      returns `200` with a list of pins.
- [ ] No pin in the response has `visibility_status == "HIDDEN"` for any
      query, regardless of `include_caveat`.
- [ ] `include_caveat=false` excludes `CAVEAT` pins; `include_caveat=true`
      includes them.
- [ ] `radius_m=10001` returns `422` (above cap).
- [ ] Pins are ordered by distance ascending — assertion in test that
      consecutive pins have non-decreasing distance from the query
      point.
- [ ] The query plan (`EXPLAIN`) uses the GIST index defined in
      phase 01 once the table holds enough rows.
- [ ] `Cache-Control: public, max-age=15` is present on the response.
- [ ] An empty result is `200` with `items: []`, not `404`.

## Pitfalls / notes

- **Earth is not flat, but for 10 km it's close enough.** PostGIS
  `ST_DWithin(geography)` does true geodesic distance. Don't try to
  compute great-circle distances in Python — the database is faster
  and more accurate.
- **Don't trust client-supplied bounding boxes.** A future bbox-based
  endpoint (`?bbox=west,south,east,north`) is reasonable, but watch
  out for antimeridian crossings (Pacific) and queries that span
  poles. Out of scope here.
- **`image_url` may be slow to render** if the image is large. Phase 09
  / 10 should request a thumbnail variant for map markers. For MVP,
  serve the original and accept the latency.
