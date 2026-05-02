"""Image upload validation and persistence."""
from __future__ import annotations
import io
import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings

log = logging.getLogger(__name__)

CHUNK = 64 * 1024  # 64 KB read chunks


async def validate_and_persist_upload(file: UploadFile, *, settings: Settings) -> Path:
    """Validate content-type, size, magic bytes, then persist to upload_dir.

    Raises HTTPException 415/413/422 on validation failure.
    Returns the Path of the saved file on success.
    """
    # 1. Content-type check
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in settings.allowed_image_types:
        raise HTTPException(415, f"Unsupported media type: {ct}")

    # 2. Stream into buffer, enforcing size limit
    buf = io.BytesIO()
    total = 0
    while chunk := await file.read(CHUNK):
        total += len(chunk)
        if total > settings.max_image_bytes:
            raise HTTPException(413, "Image exceeds maximum allowed size")
        buf.write(chunk)
    buf.seek(0)

    # 3. Magic-byte / integrity check via Pillow
    try:
        img = Image.open(buf)
        img.verify()  # consumes the pointer
    except (UnidentifiedImageError, Exception) as exc:
        raise HTTPException(415, f"Invalid image data: {exc}") from exc

    buf.seek(0)

    # 4. Persist under UUID filename
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
    dest = upload_dir / f"{uuid.uuid4().hex}{ext}"
    dest.write_bytes(buf.read())
    log.info("upload.saved path=%s size=%d", dest, total)
    return dest
