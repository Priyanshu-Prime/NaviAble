# Phase 03c — Perceptual-Hash Cache

## Goal

Don't re-run YOLO on the same photograph. Cache `VisionResult` keyed by
the image's perceptual hash, with bounded LRU eviction. Persist the hash
on the contribution row so the cache can warm from recent DB rows after
a restart.

## Prerequisites

- Phase 03a merged: `YoloVisionService` skeleton with `_cache` and
  `_cache_order` defined.
- Phase 01 merged: `contributions.image_phash` column exists.

## Deliverables

### Hash function

```python
def _compute_phash(self, image_path: Path) -> int:
    with Image.open(image_path) as img:
        return int(str(imagehash.phash(img)), 16)
```

`imagehash.phash` returns a 64-bit hash. Convert to `int` for cheap dict
keying. Two visually-identical photos hash to the same int even if their
JPEG bytes differ (re-encoded, EXIF stripped, etc.) — that is the whole
point.

### Eviction

```python
async def _remember(self, phash: int, result: VisionResult) -> None:
    async with self._lock:
        if phash in self._cache:
            return
        if len(self._cache_order) == self._cache_order.maxlen:
            evict = self._cache_order[0]
            self._cache.pop(evict, None)
        self._cache_order.append(phash)
        self._cache[phash] = result
```

`deque(maxlen=...)` handles the FIFO trim; the dict is mutated under the
lock. Read path (`self._cache.get(phash)`) is lock-free — concurrent
reads are safe on a CPython dict.

### Persistence

The verify endpoint (phase 06) writes `vision_result.image_phash` into
`contributions.image_phash` on every successful submission. Cache-warming
on startup is **out of scope here** — call it out as a future
optimisation in the failure-handling doc (03f).

## Acceptance criteria

- [ ] Calling `vision.score(path)` twice on the same image runs `_infer`
      exactly once (assert via mock or by timing the second call < 5 ms).
- [ ] Two visually-identical re-encodings of the same photo produce the
      same phash (use a fixture pair).
- [ ] After `cache_size + 1` distinct images, the oldest entry has been
      evicted; only the last `cache_size` remain.
- [ ] Cross-process: a fresh process does **not** carry cache from a
      previous one (in-memory is intentional).

## Pitfalls / notes

- The cache is in-memory and per-process. Cross-process coherence would
  add Redis to the deployment for a feature that handles duplicate
  uploads from a single moderator session — not worth it for MVP.
- Don't expand the cache to a `dict[bytes, ...]` keyed on image bytes.
  Two re-encodings of the same photo would miss the cache; phash dodges
  that.
- The `_lock` is `asyncio.Lock`, not `threading.Lock`. Eviction runs in
  the event loop; `_infer` runs on a thread pool. Keep them separate.
