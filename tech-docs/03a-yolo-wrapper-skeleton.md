# Phase 03a — `YoloVisionService` Skeleton

## Goal

The class shape and async-call discipline for the vision wrapper. Loads
weights once, exposes `score(image_path)`, and runs the blocking
Ultralytics `predict` via `asyncio.to_thread` so a slow inference call
does not block the event loop.

## Prerequisites

- Phase 02e merged: `VisionService` Protocol and `VisionResult` schema exist.
- Trained YOLOv11 weights at `settings.yolo_weights_path`.

## Deliverables

`backend/app/services/vision.py`:

```python
TARGET_CLASSES = ("ramp", "stairs", "steps", "handrail")


class YoloVisionService:
    def __init__(
        self,
        weights_path: Path,
        *,
        threshold: float = 0.205,
        cache_size: int = 256,
    ):
        self._model = YOLO(str(weights_path))
        self._threshold = threshold
        self._cache: dict[int, VisionResult] = {}
        self._cache_order: deque[int] = deque(maxlen=cache_size)
        self._lock = asyncio.Lock()

    async def score(self, image_path: Path) -> VisionResult:
        phash = await asyncio.to_thread(self._compute_phash, image_path)
        cached = self._cache.get(phash)
        if cached is not None:
            return cached
        result = await asyncio.to_thread(self._infer, image_path, phash)
        await self._remember(phash, result)
        return result

    def _infer(self, image_path: Path, phash: int) -> VisionResult: ...
    def _compute_phash(self, image_path: Path) -> int: ...
    async def _remember(self, phash: int, result: VisionResult) -> None: ...
```

`_infer` is synchronous on purpose: Ultralytics' `model.predict(...)` is
blocking, and `to_thread` is the only acceptable way to call it from an
async endpoint without serialising every request.

Threshold and `target_classes` filter happen inside `_infer` — the
endpoint never sees boxes below threshold.

## Acceptance criteria

- [ ] `YoloVisionService(weights).score(path)` is awaitable and returns
      a `VisionResult`.
- [ ] Two concurrent `score` calls run their `_infer` bodies on
      different threads (assert via `threading.get_ident()` in a test).
- [ ] Threshold `0.205` is taken from `Settings`, not hard-coded inside
      `_infer`.
- [ ] `_model` is constructed exactly once per process — wrap with a
      mock and assert call count.

## Pitfalls / notes

- **Don't run `torch.cuda.empty_cache()` in the hot path.** It is
  expensive and not what the call thinks it is doing on long-running
  servers.
- **Set `verbose=False` on `model.predict(...)`.** Ultralytics writes
  pretty per-call summaries to stdout; with structured logging (phase
  02g) those become noise.
- The lock guards the cache eviction in `_remember`. The `_infer` call
  itself is **not** locked — we want concurrency.
