# Phase 03e — Lifespan Warm-up

## Goal

The first request after deploy should not pay the model-load cost.
Force a warm-up inference inside FastAPI's `lifespan` hook so the model
is ready before any client request arrives.

## Prerequisites

- Phase 03a–c merged: `YoloVisionService` is functional end-to-end.
- Phase 02b merged: `create_app()` exists and supports `lifespan`.

## Deliverables

### Lifespan integration

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    vision = YoloVisionService(Path(settings.yolo_weights_path))
    await vision.score(Path("backend/app/static/warmup.jpg"))
    app.state.vision = vision
    # ...
    yield
```

### Warm-up image

Commit a small (≤320×320) license-clean photograph of a ramp at
`backend/app/static/warmup.jpg`. A self-shot image is fine.

The image must:
- Be a real photograph, not a procedurally generated test pattern —
  Ultralytics' first inference exercises real codepaths only on real
  inputs.
- Be small. A multi-megabyte warm-up image makes deploys slow.
- Trigger at least one detection above threshold so the entire pipeline
  (NMS, post-processing) actually runs.

## Acceptance criteria

- [ ] App boot logs include a `vision.warmup.complete` line before the
      server is marked ready.
- [ ] First real request after boot finishes in roughly the same time as
      the second request (within 20%, hand-timed). Without warm-up the
      gap is typically 5–10x.
- [ ] `app.state.vision` is set and is a `YoloVisionService` instance
      after lifespan startup.
- [ ] Warm-up failure (e.g. weights file missing) crashes lifespan with
      a clear error — the app does **not** start in a half-broken state.

## Pitfalls / notes

- Crash on warm-up failure on purpose. A boot that "succeeds" with no
  vision available is a worse outage than a boot that fails fast — the
  former returns 500s, the latter is caught by the orchestrator's
  restart loop.
- Don't warm up against a network-loaded image. The path must be a
  committed file the deployment package always carries.
- Phase 04 also adds a warm-up call. Both run sequentially in
  `lifespan` — they are not on the request path, so concurrency would
  add complexity for no user-visible win.
