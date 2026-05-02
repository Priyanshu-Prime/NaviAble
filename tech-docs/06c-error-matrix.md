# Phase 06c — Error Matrix & Tests

## Goal

Pin down the exact response for every failure mode of `/verify`, and
back each row with an integration test. The matrix is the contract the
frontend codes against.

## Prerequisites

- Phase 06a, 06b merged.

## Deliverables

### Matrix

| Condition                                            | Response                                |
|------------------------------------------------------|-----------------------------------------|
| Missing `image` field                                | `422` (FastAPI default)                 |
| Missing `review`/`latitude`/`longitude`/`rating`     | `422`                                   |
| `review` empty after `strip_whitespace`              | `422` (Pydantic `min_length=1`)         |
| `rating` not in `1..5`                               | `422`                                   |
| `latitude` out of `[-90, 90]`                        | `422`                                   |
| `longitude` out of `[-180, 180]`                     | `422`                                   |
| `image` content-type not in allowed list             | `415`                                   |
| `image` over `max_image_bytes`                       | `413`                                   |
| `image` is a corrupt JPEG (passes type, fails verify)| `201` with `score=0`, `HIDDEN`          |
| Vision service raises `VisionUnavailable`            | `503`                                   |
| NLP service raises `NlpUnavailable`                  | `503`                                   |
| DB write fails (PostGIS down, constraint violation)  | `503` and saved file is removed         |

### The "corrupt JPEG → 201 HIDDEN" branch

This is unusual but **correct**. The fusion stage is the right place for
"we couldn't see anything in the photo" to translate into "we don't
trust the contribution." Do not turn it into a `400`:

- The user is not at fault for a phone-camera artefact.
- The contribution is retained for re-evaluation per spec section 3.4.2.
- The frontend gets feedback that explains the low score.

### Cleanup on DB failure

```python
try:
    session.add(row)
    await session.commit()
except SQLAlchemyError:
    await asyncio.to_thread(saved_path.unlink, missing_ok=True)
    raise HTTPException(503, "could not persist contribution")
```

A successful upload with a failed DB write must not leave an orphaned
file on disk — the next deploy / disk-full alert pays for it otherwise.

### Integration tests

One test per row of the matrix, in
`backend/tests/api/test_verify_errors.py`. The corrupt-JPEG and
`VisionUnavailable` rows are the most useful — they exercise paths that
unit tests of the service modules don't.

## Acceptance criteria

- [ ] Every row of the matrix is exercised by an integration test.
- [ ] The `503` paths log an error with `request_id` and the underlying
      cause. The client only sees the `503`, not the cause.
- [ ] After a DB-failure test, the upload directory contains zero
      orphan files.
- [ ] No test mocks `HTTPException` — they're allowed to propagate to
      FastAPI's exception handler.

## Pitfalls / notes

- **Pydantic errors are `422`, not `400`.** Don't override this; the
  Flutter client (phase 09) parses the structured error body that
  Pydantic produces.
- **Don't catch `Exception` in the endpoint.** Each failure case has a
  specific exception type. Catching everything hides bugs and makes the
  `503` path lie about what's wrong.
- **`415` vs `422`** — content-type rejection is `415 Unsupported Media
  Type`. Don't fold it into Pydantic; the validation helper (02d) raises
  `HTTPException(415)` directly.
