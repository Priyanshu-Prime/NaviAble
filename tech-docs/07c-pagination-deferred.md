# Phase 07c — Pagination (Deferred)

## Goal

**Not built yet.** Records the design choice so a future engineer
doesn't quietly add offset-based pagination, which is the wrong shape
for spatial queries.

## Status

Deferred. Build only when the 200-row cap is regularly hit on real
traffic.

## What we'd do

Cursor pagination by **distance**, not by row offset:

```
GET /api/v1/contributions/nearby?latitude=...&longitude=...&radius_m=...
  &after_distance=842.5     # metres; pin distance from the query point
  &after_id=<uuid>          # tiebreaker for pins at exactly the same distance
```

The `find_nearby` helper changes to:

```sql
WHERE ST_DWithin(location::geography, point, :radius_m)
  AND visibility_status IN (...)
  AND (
    ST_Distance(location::geography, point) > :after_distance
    OR (ST_Distance(location::geography, point) = :after_distance
        AND id > :after_id)
  )
ORDER BY ST_Distance(location::geography, point), id
LIMIT 200;
```

The response includes a `next_cursor` field with the last pin's
`(distance, id)` tuple. Clients pass it back to fetch the next page.

## Why not offset pagination

`OFFSET 200` re-computes the entire ordered set and discards the first
200 rows. For a spatial query against a moving viewport, this is:

- **Slow.** PostGIS computes distance for every row in the radius, then
  throws most of them away.
- **Inconsistent.** New pins inserted between page fetches shift the
  offset, producing duplicates or skipped rows.

Cursor pagination has neither problem.

## When to pick this back up

Build when **either** is true:

1. The 200-row cap is exceeded in real traffic (monitor the response
   size in logs).
2. UX feedback says users in dense areas can't see all nearby pins.

## Pitfalls when it does get built

- **Distance is metres.** The cursor is a float; round to 4 decimals
  before serialising or you get URL noise.
- **The tiebreaker matters.** Two pins at the exact same lat/lon (same
  venue, two contributors) need a deterministic order; `id` works
  because UUIDs are unique.
- **The 200-row cap stays.** Pagination doesn't replace the cap; it
  lets clients walk past it explicitly.
- **`include_caveat` is part of the cursor scope.** A page-2 request
  with `include_caveat=false` while page-1 had `include_caveat=true` is
  ill-defined — return `400` if the caller mixes them.
