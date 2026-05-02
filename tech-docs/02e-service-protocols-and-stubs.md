# Phase 02e — Service-Layer Protocols & Stubs

## Goal

Define the contracts that phases 03 (vision), 04 (NLP), and 05 (fusion)
will implement, and ship constant-returning stub implementations so the
foundation phase can be tested and merged before the real models exist.

The verify endpoint in phase 06 should not be able to tell whether it's
talking to a stub or a real implementation — that's the test of a clean
seam.

## Prerequisites

- Phase 02a, 02c merged: `Settings` and `FeatureDetection` exist.

## Deliverables

`backend/app/services/vision.py`:

```python
class VisionResult(BaseModel):
    score: float                                          # max-confidence across target classes
    detections: dict[str, list[FeatureDetection]]         # keyed by class
    image_phash: int


class VisionService(Protocol):
    async def score(self, image_path: Path) -> VisionResult: ...


class StubVisionService:
    async def score(self, image_path: Path) -> VisionResult:
        return VisionResult(score=0.5, detections={}, image_phash=0)
```

`backend/app/services/nlp.py`:

```python
class NlpService(Protocol):
    async def score(self, text: str) -> float: ...   # P(LABEL_1)


class StubNlpService:
    async def score(self, text: str) -> float:
        return 0.5
```

`backend/app/services/fusion.py`:

```python
def compute_trust_score(vision: float, nlp: float, *, settings: Settings) -> float:
    # phase 05 replaces the body
    return 0.5

def assign_status(trust: float) -> Literal["PUBLIC", "CAVEAT", "HIDDEN"]:
    # phase 05 replaces the body
    return "CAVEAT"
```

Stubs are wired into `app.state.vision` / `app.state.nlp` in `lifespan`
when `settings.use_stub_models = True` (or when an env-flag is set in
tests). Phases 03/04 replace this wiring without touching the endpoint.

## Acceptance criteria

- [ ] `VisionService` and `NlpService` are `typing.Protocol` types, not
      ABCs. Stubs and real implementations satisfy them by structure.
- [ ] A mock-driven test of the verify endpoint (phase 06 stub) passes
      using `StubVisionService` and `StubNlpService`.
- [ ] Importing `services.fusion` does not import torch, ultralytics, or
      transformers. The fusion module is pure Python.

## Pitfalls / notes

- Use `typing.Protocol`, not `abc.ABC`. Protocols are duck-typed, which
  matters because the real services are constructed by their own modules
  and we don't want a hard inheritance link.
- Don't put stubs behind a flag in the production code path. They live
  for tests and for the brief window before phases 03/04 land.
- The `image_phash` field on `VisionResult` exists so the endpoint can
  persist it without recomputing the hash. Keep it on the contract even
  though the stub returns `0` — phase 03 will populate it for real.
