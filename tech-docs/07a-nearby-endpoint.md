# Phase 07a — `/contributions/nearby` Endpoint

## Goal

Expose `find_nearby` (phase 01d) over HTTP. The endpoint validates inputs,
calls the helper, and maps ORM rows to the API pin shape.

## Prerequisites

- Phase 01 merged: `find_nearby` exists in `db/queries.py`.
- Phase 02c merged: `NearbyQuery`, `NearbyResponse`, `ContributionPin`.

## Deliverables

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
    settings: Settings = Depends(get_settings),
) -> NearbyResponse:
    rows = await find_nearby(
        session,
        lat=latitude, lon=longitude, radius_m=radius_m,
        include_caveat=include_caveat, limit=200,
    )
    return NearbyResponse(items=[_to_pin(r, settings) for r in rows])


def _to_pin(row: Contribution, settings: Settings) -> ContributionPin:
    # Strip WKB into floats; compose image_url from settings + filename.
    lon, lat = row.location.coords  # via geoalchemy2.shape.to_shape
    return ContributionPin(
        id=row.id,
        latitude=lat,
        longitude=lon,
        trust_score=row.trust_score,
        visibility_status=row.visibility_status,   # never HIDDEN by find_nearby's filter
        rating=row.rating,
        text_note=row.text_note,
        image_url=_compose_image_url(row.image_path, settings),
    )
```

The endpoint is read-only, doesn't write, doesn't mutate session state.
Default `radius_m` is **not** set — the caller must specify. This is the
"no surprises" rule from the spec.

## Acceptance criteria

- [ ] `GET /api/v1/contributions/nearby?latitude=12.97&longitude=77.59
      &radius_m=500` returns `200` with a list of pins.
- [ ] Calling without `radius_m` returns `422`.
- [ ] `radius_m=10001` returns `422`.
- [ ] No pin in any response has `visibility_status == "HIDDEN"`,
      regardless of `include_caveat` value.
- [ ] `include_caveat=false` excludes `CAVEAT` pins.
- [ ] Pins are ordered by distance ascending — assertion checks
      consecutive pins have non-decreasing computed distance from the
      query point.
- [ ] Empty result is `200` with `items: []`, not `404`.

## Pitfalls / notes

- **Decoding WKB is `geoalchemy2.shape.to_shape`**, not a hand-written
  parser. Don't roll your own.
- **Don't return WKB or WKT in the response.** Frontends parse JSON,
  not WKB. Always split into `latitude` / `longitude` floats.
- The `_to_pin` helper lives in the router file. It's small enough that
  hoisting it to a separate module adds noise.
- The 200-row cap is enforced inside `find_nearby` (phase 01d). Don't
  duplicate the limit at the endpoint.
