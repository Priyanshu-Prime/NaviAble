# Phase 06b — Concurrency Contract

## Goal

The two model calls **must** run concurrently. User-facing latency is
the slower of the two, not their sum. This phase locks in the contract
with a test that catches a future regression.

## Prerequisites

- Phase 06a merged.

## Deliverables

### Implementation rule

The vision and NLP service calls inside `/verify` are awaited via a
single `asyncio.gather(...)`:

```python
vision_result, nlp_score = await asyncio.gather(
    vision.score(saved_path),
    nlp.score(payload.review),
)
```

Anti-patterns to reject in code review:

- `vision_result = await vision.score(...)` followed by
  `nlp_score = await nlp.score(...)` — serialised, doubles latency.
- A `for task in [...]: await task` loop — same as above.
- `gather` with one branch already awaited — pointless.

### Regression test

`backend/tests/api/test_verify_concurrency.py`:

```python
async def test_vision_and_nlp_run_concurrently(client, app):
    sleep_s = 1.0

    class SlowVision:
        async def score(self, _path):
            await asyncio.sleep(sleep_s)
            return VisionResult(score=0.5, detections={}, image_phash=0)

    class SlowNlp:
        async def score(self, _text):
            await asyncio.sleep(sleep_s)
            return 0.5

    app.state.vision = SlowVision()
    app.state.nlp = SlowNlp()

    started = time.perf_counter()
    resp = await client.post("/api/v1/verify", files=..., data=...)
    elapsed = time.perf_counter() - started

    assert resp.status_code == 201
    assert elapsed < 1.5, f"verify took {elapsed:.2f}s — branches not concurrent"
```

The 1.5 s budget is the 1 s parallel floor plus a generous 0.5 s for
serialisation, DB writes, and test overhead. Tighten it only when the
suite proves stable.

## Acceptance criteria

- [ ] The concurrency test passes consistently in CI (≥10 consecutive
      runs without flake).
- [ ] Forcing the endpoint to serialise (replace `gather` with two
      sequential awaits) makes the test fail with a clear timing message.
- [ ] No other test in the suite uses the `SlowVision`/`SlowNlp` mocks
      with shorter sleeps to "speed up" the contract — the 1 s floor is
      load-bearing.

## Pitfalls / notes

- **`asyncio.gather` propagates exceptions.** If vision raises, NLP is
  cancelled. Both wrappers must handle `CancelledError` cleanly — phase
  03f and 04c already cover this.
- **Don't add `return_exceptions=True` to `gather`.** Hiding partial
  failures behind tuple unpacking is a footgun; let them propagate so
  06c's error matrix can map them to the right status code.
- **Test runner matters.** `pytest-asyncio` with the default event loop
  is fine; a custom event loop policy in CI could mask serialisation.
  If the test is flaky, suspect the runner before suspecting the code.
