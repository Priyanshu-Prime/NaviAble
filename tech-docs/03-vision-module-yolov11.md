# Phase 03 — Vision Verification Module (YOLOv11)

## Goal

Implement the production-time wrapper around the fine-tuned YOLOv11 detector
described in Chapter 3 of the report. The wrapper is the only code that
should know about Ultralytics, model weight paths, or torch tensors —
everything upstream sees a clean `VisionService.score(image_path)` call.

The wrapper must:

1. Load the fine-tuned weights once at process start.
2. Run inference on a single image and return per-class confidences plus
   bounding boxes for the four target classes.
3. Use a perceptual-hash cache so repeated submissions of the same
   photograph do not re-run the GPU. (Spec calls this out explicitly.)
4. Surface a single normalised `score: float` in `[0, 1]` that the fusion
   stage in phase 05 will consume.

## Prerequisites

- Phase 02 merged: `VisionService` Protocol and `VisionResult` schema exist.
- Trained YOLOv11 weights from `YoloModel11/runs/...` — confirm with the
  vision sub-team which run is the production checkpoint and pin its path
  in `settings.yolo_weights_path`. The report's Chapter 4 numbers
  (mAP@0.5 of 0.89 on validation, 0.7994 on test) are the bar to beat;
  do not deploy a checkpoint below that.

## Spec details (from the project specification)

| Field              | Value                                |
|--------------------|--------------------------------------|
| Target classes     | `ramp`, `stairs`, `steps`, `handrail`|
| Detection threshold| `0.205` (lower than YOLO default 0.25)|
| Output             | Per-feature score in `[0, 1]` + bboxes|
| Cache              | In-memory, keyed on perceptual hash  |

## Current state

- `backend/app/services/ml.py` contains some inference glue. Most of it
  will be moved out and replaced; this phase rewrites the vision side
  cleanly under `services/vision.py`.
- `YoloModel11/` holds training outputs and weight files — keep those
  there; the runtime wrapper reads from that path, it does not move
  weights into `backend/`.

## Deliverables

### 1. The wrapper module

`backend/app/services/vision.py`:

```python
TARGET_CLASSES = ("ramp", "stairs", "steps", "handrail")

class YoloVisionService:
    def __init__(self, weights_path: Path, *, threshold: float = 0.205, cache_size: int = 256):
        self._model = YOLO(str(weights_path))            # ultralytics.YOLO
        self._threshold = threshold
        self._cache: dict[int, VisionResult] = {}        # phash -> result
        self._cache_order: deque[int] = deque(maxlen=cache_size)
        self._lock = asyncio.Lock()                      # guards the LRU eviction

    async def score(self, image_path: Path) -> VisionResult:
        phash = await asyncio.to_thread(self._compute_phash, image_path)
        cached = self._cache.get(phash)
        if cached is not None:
            return cached
        result = await asyncio.to_thread(self._infer, image_path, phash)
        await self._remember(phash, result)
        return result
```

The actual inference happens in `_infer`, which is a synchronous function
called via `asyncio.to_thread`. That is the only acceptable way to call
the blocking `model.predict(...)` from an async endpoint without
serialising every request through one event loop slot.

### 2. Class score reduction

The fusion stage takes one number per contribution. The wrapper computes:

```python
def _aggregate_score(detections_by_class: dict[str, list[Detection]]) -> float:
    """Return the max confidence across all detected target-class boxes,
    or 0.0 if nothing was detected above threshold."""
    confidences = [d.confidence for boxes in detections_by_class.values() for d in boxes]
    return max(confidences, default=0.0)
```

We deliberately use `max` rather than `mean`. A photograph that contains
one clearly visible ramp and zero of the other classes should score high,
not be diluted by zeroes. If a future iteration wants to weight specific
classes (a ramp is more relevant than a handrail for wheelchair access),
that decision belongs here, with a recorded rationale.

### 3. Perceptual hash

Use `imagehash.phash(Image.open(path))`. Convert to `int` for cheap dict
keying. Store the resulting int back on the contribution row
(`image_phash` column from phase 01) when the verify endpoint persists
the row — that way, future cache lookups can survive process restarts
by warming from recent DB rows.

The cache is in-memory and per-process. That is intentional. Cross-process
cache coherency adds Redis to the deployment for a feature that handles
duplicate uploads from a single moderator session — not worth it.

### 4. Bounding box format

Return boxes normalised to `[0, 1]` along each axis:

```python
class FeatureDetection(BaseModel):
    confidence: float                          # 0..1
    bbox: tuple[float, float, float, float]    # x1, y1, x2, y2 normalised
```

Normalised boxes survive image resizing on the frontend. Pixel boxes do not.

### 5. Warm load

The model loads on first request by default with Ultralytics, which
makes the first request after deploy slow. Force a warm-up at app start
in `lifespan`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    vision = YoloVisionService(settings.yolo_weights_path)
    await vision.score(Path("backend/app/static/warmup.jpg"))   # tiny ramp image
    app.state.vision = vision
    yield
```

Commit a small warmup image (a 320×320 placeholder photograph of a ramp
will do — license-free or self-shot).

### 6. Failure modes the wrapper handles

- **Corrupt image**: `Image.open(...)` raises; return a `VisionResult`
  with `score=0.0, detections={}`. Do not raise to the endpoint — a bad
  image means the contribution simply earns zero on the vision side and
  lets the fusion stage drag its trust score down. Log the error with
  the request ID.
- **Model OOM / load failure**: raise `VisionUnavailable`. The verify
  endpoint catches this and returns `503` so the client can retry.
  Do **not** silently degrade to "vision score = 0" on infrastructure
  failures, only on per-image failures — the difference matters because
  one is recoverable from the user's side and the other is not.

## Acceptance criteria

- [ ] `vision.score(path_to_ramp_photo)` returns a `VisionResult` with
      `score >= 0.5` (use a curated test image with an obvious ramp).
- [ ] `vision.score(path_to_blank_photo)` returns `score == 0.0` and
      empty detections.
- [ ] Calling `vision.score` twice on the same image runs inference once
      (assert via mock or by timing the second call < 5 ms).
- [ ] Bounding boxes returned are all in `[0, 1]^4`.
- [ ] App startup completes warm-up; first real request after boot
      finishes in roughly the same time as the second request.
- [ ] A corrupt JPEG payload (truncated bytes) yields `score=0.0`, not
      a 500.
- [ ] Threshold `0.205` is read from settings, not hard-coded inside the
      module — confirms the spec value is configurable for moderators.

## Pitfalls / notes

- **Don't run `torch.cuda.empty_cache()` in the hot path.** It is
  expensive and not what the call thinks it is doing on long-running
  servers.
- **Do not let `ultralytics` print to stdout.** Set `verbose=False` on
  `model.predict(...)`. Otherwise the inference logs swamp request logs
  and become useless.
- **Test images must not leak into git.** Put fixtures under
  `backend/tests/fixtures/images/` and add to `.gitignore` if any are
  large; commit only small, license-clean ones.
- The `score` aggregation choice (`max` over classes) is a design
  decision. If you change it, update this doc and phase 05 in the same
  PR.
