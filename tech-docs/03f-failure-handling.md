# Phase 03f — Vision Failure Handling

## Goal

Distinguish per-image failures (corrupt photo, unreadable bytes) from
infrastructure failures (model OOM, weights file gone). The first should
not raise; the second must.

## Prerequisites

- Phase 03a–e merged: `YoloVisionService` is functional and warmed up.

## Deliverables

### Per-image failure: degrade gracefully

```python
async def score(self, image_path: Path) -> VisionResult:
    try:
        phash = await asyncio.to_thread(self._compute_phash, image_path)
    except (UnidentifiedImageError, OSError) as e:
        log.warning("vision.image_unreadable", path=str(image_path), error=str(e))
        return VisionResult(score=0.0, detections={}, image_phash=0)
    # ... cache + infer path
```

A corrupt JPEG, truncated bytes, or a non-image payload that somehow
made it past phase 02d's validation should produce
`VisionResult(score=0.0, detections={}, image_phash=0)`. The fusion
stage (phase 05) sees a low score and the contribution lands in
`HIDDEN`. The **user is not at fault** for a phone-camera artefact —
this is not a `400`.

### Infrastructure failure: raise

```python
class VisionUnavailable(RuntimeError):
    """The vision model is not available — process is in a bad state."""


async def score(self, image_path: Path) -> VisionResult:
    # ...
    try:
        result = await asyncio.to_thread(self._infer, image_path, phash)
    except torch.cuda.OutOfMemoryError as e:
        log.error("vision.oom", error=str(e))
        raise VisionUnavailable("CUDA OOM") from e
```

Phase 06's verify endpoint catches `VisionUnavailable` and returns
`503`. Do **not** silently degrade to "vision score = 0" on
infrastructure failures, only on per-image failures.

The two cases differ because one is recoverable from the user's side
(retake the photo) and the other is not (operator must intervene).

### Future optimisation: cache warm-up from DB

Out of scope for this phase, but recorded so it isn't re-discovered:
a startup task can query the most recent N rows from `contributions`,
read their `image_phash` and `detected_features`, and pre-populate
`_cache`. Worth ~5–10% latency wins after a deploy if traffic patterns
favour repeat photos. Revisit only if metrics justify it.

## Acceptance criteria

- [ ] A truncated JPEG payload yields `VisionResult(score=0.0, ...)` and
      a warning log line with `request_id`. Endpoint returns `201` with
      `HIDDEN` status.
- [ ] Forcing `_infer` to raise `OutOfMemoryError` causes the endpoint
      to return `503`, not `500` and not `201`.
- [ ] A missing weights file at startup crashes lifespan, not the first
      request.
- [ ] No per-image failure path silently increments a "vision skipped"
      counter — every degradation is logged with the request ID.

## Pitfalls / notes

- Don't catch `Exception` broadly in `score`. The two cases above are
  the only ones we want to handle here; everything else propagates and
  becomes a `500` via the global handler.
- `CancelledError` (from `asyncio.gather` cancelling the other branch)
  must propagate — do not swallow it inside `_infer`.
- The "score=0 on corrupt image" rule is the design intent of fusion
  (phase 05). Changing it requires updating both docs in the same PR.
