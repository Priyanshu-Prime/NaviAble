# Phase 06 — `POST /api/v1/verify`

## Goal

Ship the canonical contribution endpoint. It accepts a multipart upload
(image + review + lat/lon + rating), validates at the edge, runs the two
AI checks **concurrently**, fuses their scores, persists the row with the
right `visibility_status`, and returns the result for the frontend to
display.

This is the central moment in the system. Everything earlier is
infrastructure for this endpoint to do its job in under a few seconds.

## Prerequisites

Phases 01–05 merged. Specifically the endpoint imports:

- `services.vision.YoloVisionService` (phase 03)
- `services.nlp.RobertaNlpService` (phase 04)
- `services.fusion.compute_trust_score`, `assign_status` (phase 05)
- `db.models.Contribution`, `db.session.get_session` (phase 01)
- `schemas.contribution.{ContributionCreate, ContributionResponse}` (phase 02)

## Spec (from the project specification)

| Field           | Value                                |
|-----------------|--------------------------------------|
| Method + path   | `POST /api/v1/verify`                |
| Content-Type    | `multipart/form-data`                |
| Form fields     | `image: file, review: str, latitude: float, longitude: float, rating: int` |
| Validation      | Pydantic v2 at the edge, `422` on failure |
| Concurrency     | `asyncio.gather` over vision + NLP   |
| Inference       | Each model wrapped via `asyncio.to_thread` |

## Current state

`backend/app/api/routers/verify.py` exists with partial code. This phase
rewrites it from the description below — do not patch into the existing
file piecewise, because the orchestration shape needs to be exact.

## Deliverables

### 1. The endpoint

`backend/app/api/routers/verify.py`:

```python
router = APIRouter(prefix="/api/v1", tags=["verify"])

@router.post("/verify", response_model=ContributionResponse, status_code=201)
async def verify(
    image: UploadFile = File(...),
    review: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    rating: int = Form(...),
    request: Request = ...,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ContributionResponse:
    payload = ContributionCreate(
        review=review, latitude=latitude, longitude=longitude, rating=rating,
    )

    saved_path = await validate_and_persist_upload(image, settings=settings)

    vision: VisionService = request.app.state.vision
    nlp: NlpService = request.app.state.nlp

    vision_result, nlp_score = await asyncio.gather(
        vision.score(saved_path),
        nlp.score(payload.review),
    )

    trust = compute_trust_score(vision_result.score, nlp_score, settings=settings)
    status_ = assign_status(trust)

    row = Contribution(
        location=f"SRID=4326;POINT({payload.longitude} {payload.latitude})",
        image_path=str(saved_path),
        image_phash=vision_result.image_phash,
        text_note=payload.review,
        rating=payload.rating,
        vision_score=vision_result.score,
        nlp_score=nlp_score,
        trust_score=trust,
        visibility_status=status_,
        detected_features=vision_result.detections,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    return ContributionResponse(
        id=row.id,
        trust_score=trust,
        vision_score=vision_result.score,
        nlp_score=nlp_score,
        visibility_status=status_,
        detected_features=vision_result.detections,
    )
```

The body is short on purpose. The endpoint is a wiring layer — every
non-trivial decision lives in a service module that has its own tests.

### 2. Concurrency contract

The two `to_thread`-wrapped inference calls must run concurrently. Verify
this is true with a test that mocks both services to sleep for 1 s and
asserts the request completes in roughly 1 s, not 2 s. If concurrency is
silently broken (e.g. someone awaits one before scheduling the other)
this test catches it.

### 3. Error matrix

| Condition                                    | Response                              |
|----------------------------------------------|---------------------------------------|
| Missing `image` field                        | `422` (FastAPI default)               |
| Missing `review` / `latitude` / `longitude` / `rating` | `422`                       |
| `review` is empty after strip                | `422` (Pydantic `min_length=1`)       |
| `rating` not in `1..5`                       | `422`                                 |
| `latitude` out of `[-90, 90]`                | `422`                                 |
| `longitude` out of `[-180, 180]`             | `422`                                 |
| `image` content-type not in allowed list     | `415`                                 |
| `image` over `max_image_bytes`               | `413`                                 |
| `image` is a corrupt JPEG                    | `score=0` returned, `201`, `HIDDEN`   |
| Vision service raises `VisionUnavailable`    | `503`                                 |
| NLP service raises `NlpUnavailable`          | `503`                                 |
| DB write fails (e.g. PostGIS down)           | `503` (and the saved file should be cleaned up) |

The "corrupt JPEG → 201 with HIDDEN" branch is unusual but correct. The
fusion stage is exactly the right place for "we couldn't see anything in
the photo" to translate into "we don't trust the contribution." Do not
turn it into a `400` — the user is not at fault for a phone-camera
artefact.

### 4. Idempotency (deferred but plan-for)

Out of scope for the first cut, but document here so it is not
re-discovered: a contributor could submit the same photo + text twice
in quick succession (mobile retry). When phase 11's load testing or a
production incident shows this is happening, add an idempotency-key
header that the client generates per-submission. Until then, the
perceptual-hash cache in the vision module is the only defence and that
is fine for MVP.

### 5. Response shape

The response intentionally surfaces `vision_score`, `nlp_score`, and
`detected_features` to the client. The frontend in phase 09 uses these to
explain the Trust Score on the result screen — "we saw a ramp at 87%
confidence, your text scored 64%" is much more useful feedback than a
single opaque number. Do not strip these in a future "API hardening" pass
without checking the frontend first.

### 6. Retire `predict.py`

Once `/verify` is merged and the frontend has switched over (phase 09),
delete `backend/app/api/routers/predict.py` and remove its registration
from `main.py`. Two endpoints doing similar things is a footgun. Do this
in the same PR that switches the frontend; do not leave `/predict`
behind "just in case."

## Acceptance criteria

- [ ] `curl -F image=@ramp.jpg -F review="ramp at the back" -F latitude=12.97
       -F longitude=77.59 -F rating=5 http://localhost:8000/api/v1/verify`
      returns `201` with a complete `ContributionResponse`.
- [ ] The error matrix above is exercised by integration tests, every
      row covered.
- [ ] Concurrency test: with both services mocked to `sleep(1)`, total
      request time is `< 1.5 s` (allowing a buffer over the 1 s parallel
      floor).
- [ ] After a successful request, a row exists in `contributions` with
      the expected lat/lon (verify with `ST_AsText(location)`) and
      `visibility_status` matching the band of the trust score.
- [ ] `HIDDEN` rows persist; they are present in the DB, never returned
      by the discovery endpoint in phase 07.
- [ ] When the DB write fails after a successful upload, the saved
      image file is removed from disk (no orphan files).

## Pitfalls / notes

- **The `image_path` is local in dev.** For prod, swap to S3-compatible
  object storage. Keep the path/URL split in the schema (phase 01) so
  this is a one-file change later.
- **`asyncio.gather` propagates exceptions.** If vision raises and NLP
  is still running, NLP is cancelled. Make sure both wrappers handle
  `CancelledError` cleanly — it is fine to let it propagate, but do not
  swallow it inside `_infer`.
- **Don't compute the perceptual hash twice.** It comes back from
  `VisionService.score` already (phase 03). Do not also compute it at
  the endpoint — that defeats the cache.
- **No silent retry inside the endpoint.** If vision fails, return `503`
  and let the frontend's Dio interceptor decide whether to retry. Hidden
  retries make latency reasoning impossible.
