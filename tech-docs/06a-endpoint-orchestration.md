# Phase 06a — `/verify` Endpoint Orchestration

## Goal

Wire the verify endpoint body. The function is short on purpose: every
non-trivial decision is implemented in a service module that has its own
tests. This phase only assembles them.

## Prerequisites

- Phases 01–05 merged.

## Deliverables

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

The shape is the contract. **Do not** patch this onto the existing
`verify.py` piecewise — rewrite the file from this template, because
the orchestration sequence (validate → upload → gather → fuse → persist
→ respond) needs to be exact.

## Acceptance criteria

- [ ] `curl -F image=@ramp.jpg -F review="ramp at the back" -F
       latitude=12.97 -F longitude=77.59 -F rating=5
       http://localhost:8000/api/v1/verify` returns `201` with a complete
      `ContributionResponse`.
- [ ] After a successful request, a row exists in `contributions` with
      the expected lat/lon (verify with `ST_AsText(location)`).
- [ ] `visibility_status` on the persisted row matches the band of the
      trust score.
- [ ] The endpoint body is < 60 lines. If it grows, the work belongs
      in a service module instead.

## Pitfalls / notes

- **Don't recompute the perceptual hash at the endpoint.** It comes
  back from `VisionService.score` already (phase 03c). Recomputing
  defeats the cache.
- **`image_path` is local in dev.** For prod, swap to S3-compatible
  object storage. The path/URL split in the schema (phase 01) makes
  this a one-file change later.
- **No silent retry inside the endpoint.** If vision or NLP fails,
  surface it (06c). The frontend's Dio interceptor decides whether to
  retry.
