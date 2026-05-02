# Phase 02d — Image Validation & Persistence Helper

## Goal

One helper that takes a `UploadFile`, enforces type/size/integrity rules,
writes the bytes to disk under a UUID filename, and returns the resulting
path. Phase 06's `/verify` endpoint calls this once and trusts the result.

## Prerequisites

- Phase 02a merged: `Settings` provides `upload_dir`, `max_image_bytes`,
  `allowed_image_types`.

## Deliverables

`backend/app/core/uploads.py`:

```python
async def validate_and_persist_upload(
    file: UploadFile, *, settings: Settings
) -> Path:
    # 1. Reject if file.content_type not in settings.allowed_image_types -> 415.
    # 2. Stream bytes in chunks; abort with 413 if running total exceeds
    #    settings.max_image_bytes (do NOT read everything then check).
    # 3. Magic-byte sniff: `Image.open(BytesIO(...))` + `Image.verify()`
    #    catches a `.jpg` extension on a non-image payload.
    # 4. Persist to settings.upload_dir under `f"{uuid4().hex}{ext}"`.
    # 5. Return the saved Path.
```

Errors raise `HTTPException` with the documented status codes. The verify
endpoint in phase 06 propagates them unchanged.

## Acceptance criteria

- [ ] `text/plain` payload → `415`.
- [ ] Payload with `Content-Length` over `max_image_bytes` → `413`,
      and the partial file is **not** left on disk.
- [ ] A `.jpg` extension wrapping non-image bytes (e.g. `b"hello"` saved
      as `fake.jpg`) → `415` after magic-byte check.
- [ ] A truncated JPEG that opens but `Image.verify()` rejects → `415`.
- [ ] Successful path: the returned `Path` exists and contains the
      uploaded bytes byte-for-byte.

## Pitfalls / notes

- **`UploadFile` does not enforce size.** FastAPI streams the upload; the
  oversize check has to happen as you read it, not after. Read in chunks
  with a running counter and bail early.
- `Content-Length` from the client is a hint, not a guarantee. Enforce on
  the actual byte stream too.
- `Image.verify()` consumes the file pointer. If you want to keep the
  bytes for persistence, read into `BytesIO` first, verify, then write
  the buffer to disk.
- Pillow is the right tool for magic-byte sniffing here. Don't roll your
  own header parser for JPEG/PNG/WebP — there are too many edge cases.
- Cleanup on later failure (e.g. DB write fails after the image was
  saved) is the verify endpoint's responsibility, not this helper's.
