# Phase 06d — Idempotency (Deferred)

## Goal

**Not built yet.** Captures the design for an `Idempotency-Key`-style
header so it isn't re-discovered later. The MVP relies on the perceptual
hash cache (03c) as a partial mitigation; that is intentional.

## Status

Deferred. Build only when phase 11 load testing or production traffic
shows duplicate submissions arriving in tight retries.

## What we'd do

Accept a client-generated `Idempotency-Key` header. Store seen keys in
a small TTL store (Postgres table or in-process LRU keyed by
`(user_id, key)` — but there's no `user_id` yet, so the key alone).

```python
@router.post("/verify", ...)
async def verify(
    ...,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        prior = await idempotency_store.get(idempotency_key)
        if prior is not None:
            return prior   # cached ContributionResponse
    # ... normal path
    if idempotency_key:
        await idempotency_store.put(idempotency_key, response, ttl=24 * 3600)
    return response
```

### Why not now

- The phash cache (03c) already collapses repeat submissions of the same
  photo within process lifetime.
- Without `user_id`, key collisions across clients are theoretically
  possible (UUID v4 makes them vanishingly unlikely in practice, but it's
  a thing to think about).
- It's a feature pulled from REST best practice, not a spec requirement.

### When to pick this back up

Add it when **either** is true:

1. Production logs show the same `image_phash + text_note + lat/lon`
   tuple persisting twice within seconds, indicating client-side retry
   storms.
2. The mobile client team adds an offline-resubmit feature that needs
   strong client-side guarantees.

### Open design questions

- **Storage:** Postgres table with a TTL cleanup job, or Redis? Redis
  adds infra; Postgres adds schema. Decide when picking the work back up.
- **Replay window:** 24 hours seems right for retry storms; longer
  windows balloon the store with no payoff.
- **Failed requests:** Should a `503` be cached and replayed? Probably
  not — the client should be allowed to retry a `503`. Cache only `2xx`.

## Pitfalls when it does get built

- Cache the **response body**, not the request. Replaying based on the
  request alone re-runs the models (defeats the point) and requires
  storing the upload (security/quota issues).
- Don't tie idempotency to the perceptual hash. They solve different
  problems: phash dedupes by content, idempotency dedupes by client
  intent. A client legitimately resubmitting the same photo (same key,
  same image) is one thing; two different clients submitting the same
  photo is another.
