# Phase 03 — Backend: place-aware /verify, location resolution, and training export

**Status:** not started
**Depends on:** phase 01 (places + place_id FK), phase 02 (GooglePlacesService, EXIF)
**Affects:** `backend/app/api/routers/verify.py`, `backend/app/schemas/contribution.py`, `backend/app/cli/`, `backend/app/services/`, new `backend/app/api/routers/training.py`

## Goal

1. Make `/api/v1/verify` **place-aware**: it accepts an optional `place_id`,
   else resolves coordinates → place via reverse-geocode + upsert. The
   resulting `Contribution` row is FK-linked to a `Place`. The place's
   denormalised aggregates are recomputed in the same transaction so the
   map view always reads consistent data.
2. Add a **location resolution chain** for the multipart request:
   `place_id` (best) → `(lat,lon)` from form → EXIF GPS from photo → reverse
   geocode of address string. Reject the request only if all four fail.
3. Add **`POST /api/v1/training/export`** + a CLI entrypoint that produces a
   YOLO-format detection dataset *and* a RoBERTa text-classification CSV
   from PUBLIC contributions, recorded in `training_exports`.

---

## Deliverables

### 1. Schema updates

Edit `backend/app/schemas/contribution.py`:

```python
from typing import Annotated, Dict, List, Literal, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class ContributionCreate(BaseModel):
    review: Annotated[str, StringConstraints(min_length=1, max_length=2000, strip_whitespace=True)]
    rating: Annotated[int, Field(ge=1, le=5)]
    # All four are optional; the resolver in verify.py picks the best signal.
    google_place_id: Optional[str] = Field(default=None, max_length=255)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    address: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _at_least_one_location_signal(self) -> "ContributionCreate":
        if self.google_place_id:
            return self
        if self.latitude is not None and self.longitude is not None:
            return self
        if self.address:
            return self
        # EXIF is checked server-side; allow empty-but-photo-has-GPS case
        return self


class ContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    place_id: Optional[UUID]
    place_name: Optional[str]
    trust_score: float
    vision_score: float
    nlp_score: float
    visibility_status: Literal["PUBLIC", "CAVEAT", "HIDDEN"]
    detected_features: Dict[str, List["FeatureDetection"]]


class FeatureDetection(BaseModel):
    confidence: float
    bbox: Tuple[float, float, float, float]


class ContributionPin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    place_id: Optional[UUID]
    latitude: float
    longitude: float
    trust_score: float
    visibility_status: Literal["PUBLIC", "CAVEAT"]
    rating: int
    text_note: str
    image_url: Optional[str]


class NearbyResponse(BaseModel):
    items: List[ContributionPin]


ContributionResponse.model_rebuild()
```

### 2. Location resolver

Create `backend/app/services/location_resolver.py`:

```python
"""Resolve a contribution's location from one of: place_id / coords / EXIF / address.

Chain priority (most authoritative first):
  1. `google_place_id` — explicit user choice. Always wins.
  2. `(latitude, longitude)` from form fields — device GPS at submit time.
  3. EXIF GPS embedded in the uploaded photo.
  4. Reverse-geocode of `address` string.

Returns the resolved Place row (upserted) and effective (lat, lon).
Raises HTTPException(422) if every signal is missing or invalid.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Place
from app.db.queries import upsert_place
from app.services.exif import extract_gps
from app.services.google_places import GooglePlacesService, GooglePlacesUnavailable

log = logging.getLogger(__name__)


async def resolve_place(
    session: AsyncSession,
    google: GooglePlacesService,
    *,
    google_place_id: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    address: Optional[str],
    image_path: Path,
) -> Tuple[Place, float, float]:
    # 1. explicit place id
    if google_place_id:
        existing = (
            await session.execute(
                select(Place).where(Place.google_place_id == google_place_id)
            )
        ).scalar_one_or_none()
        if existing:
            from geoalchemy2.shape import to_shape
            pt = to_shape(existing.location)
            return existing, pt.y, pt.x
        try:
            details = await google.details(place_id=google_place_id)
        except GooglePlacesUnavailable as exc:
            raise HTTPException(503, "Place lookup unavailable") from exc
        if not details:
            raise HTTPException(422, "Unknown google_place_id")
        loc = details["geometry"]["location"]
        place = await upsert_place(
            session,
            google_place_id=google_place_id,
            name=details.get("name", ""),
            formatted_address=details.get("formatted_address"),
            lat=float(loc["lat"]),
            lon=float(loc["lng"]),
            google_types=details.get("types", []),
        )
        return place, float(loc["lat"]), float(loc["lng"])

    # 2. raw coordinates
    if latitude is not None and longitude is not None:
        return await _resolve_from_coords(session, google, latitude, longitude)

    # 3. EXIF GPS
    gps = extract_gps(image_path)
    if gps is not None:
        log.info("verify.exif_gps lat=%s lon=%s", *gps)
        return await _resolve_from_coords(session, google, gps[0], gps[1])

    # 4. address reverse geocode
    if address:
        try:
            geo = await google.reverse_geocode_address(address) if hasattr(
                google, "reverse_geocode_address"
            ) else None
        except GooglePlacesUnavailable as exc:
            raise HTTPException(503, "Geocoding unavailable") from exc
        # Simpler: forward-geocode the address
        # (Add `geocode_address` to GooglePlacesService — see snippet below)
        if geo and "geometry" in geo:
            loc = geo["geometry"]["location"]
            return await _resolve_from_coords(session, google, float(loc["lat"]), float(loc["lng"]))

    raise HTTPException(
        422,
        "Could not determine location: provide google_place_id, "
        "(latitude,longitude), an address, or upload a geo-tagged photo.",
    )


async def _resolve_from_coords(
    session: AsyncSession,
    google: GooglePlacesService,
    lat: float,
    lon: float,
) -> Tuple[Place, float, float]:
    """Reverse-geocode (lat,lon) → place_id → upsert."""
    geo = await google.reverse_geocode(lat=lat, lon=lon)
    if not geo:
        raise HTTPException(
            422, "Could not match coordinates to a Google place"
        )
    pid = geo.get("place_id")
    if not pid:
        raise HTTPException(422, "Reverse-geocode returned no place_id")
    types = geo.get("types", [])
    place = await upsert_place(
        session,
        google_place_id=pid,
        name=geo.get("formatted_address", "Unnamed place").split(",")[0],
        formatted_address=geo.get("formatted_address"),
        lat=lat,
        lon=lon,
        google_types=types,
    )
    return place, lat, lon
```

Add a `geocode_address` method to `GooglePlacesService` (phase 02 file):

```python
async def geocode_address(self, *, address: str) -> Optional[dict[str, Any]]:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": self._settings.google_places_api_key}
    resp = await self._client.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK":
        return None
    results = data.get("results") or []
    return results[0] if results else None
```

(And update the resolver to call `geocode_address` instead of the
non-existent `reverse_geocode_address`.)

### 3. Rewrite the verify endpoint

Replace `backend/app/api/routers/verify.py`:

```python
"""POST /api/v1/verify — place-aware contribution + dual-AI trust scoring."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_google_places
from app.core.config import Settings, get_settings
from app.core.uploads import validate_and_persist_upload
from app.db.models import Contribution
from app.db.queries import recompute_place_aggregates
from app.db.session import get_session
from app.schemas.contribution import ContributionCreate, ContributionResponse
from app.services.fusion import assign_status, compute_trust_score
from app.services.google_places import GooglePlacesService
from app.services.location_resolver import resolve_place
from app.services.nlp import NlpUnavailable
from app.services.vision import VisionUnavailable

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["verify"])


@router.post("/verify", response_model=ContributionResponse, status_code=201)
async def verify(
    request: Request,
    image: UploadFile = File(...),
    review: str = Form(...),
    rating: int = Form(...),
    google_place_id: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    address: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    google: GooglePlacesService = Depends(get_google_places),
) -> ContributionResponse:
    payload = ContributionCreate(
        review=review,
        rating=rating,
        google_place_id=google_place_id,
        latitude=latitude,
        longitude=longitude,
        address=address,
    )

    saved_path = await validate_and_persist_upload(image, settings=settings)

    place, eff_lat, eff_lon = await resolve_place(
        session,
        google,
        google_place_id=payload.google_place_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        image_path=saved_path,
    )

    vision_svc = request.app.state.vision
    nlp_svc = request.app.state.nlp

    try:
        vision_result, nlp_score = await asyncio.gather(
            vision_svc.score(saved_path),
            nlp_svc.score(payload.review),
        )
    except VisionUnavailable as exc:
        raise HTTPException(503, "Vision service unavailable") from exc
    except NlpUnavailable as exc:
        raise HTTPException(503, "NLP service unavailable") from exc

    trust = compute_trust_score(vision_result.score, nlp_score, settings=settings)
    status_ = assign_status(trust)

    row = Contribution(
        place_id=place.id,
        location=f"SRID=4326;POINT({eff_lon} {eff_lat})",
        image_path=str(saved_path),
        image_phash=vision_result.image_phash,
        text_note=payload.review,
        rating=payload.rating,
        vision_score=vision_result.score,
        nlp_score=nlp_score,
        trust_score=trust,
        visibility_status=status_,
        detected_features={
            cls: [d.model_dump() for d in dets]
            for cls, dets in vision_result.detections.items()
        },
    )
    try:
        session.add(row)
        await session.flush()
        await recompute_place_aggregates(session, place.id)
        await session.commit()
        await session.refresh(row)
    except Exception as exc:
        await asyncio.to_thread(saved_path.unlink, missing_ok=True)
        log.exception("verify.commit_failed")
        raise HTTPException(503, "Could not persist contribution") from exc

    log.info(
        "verify.ok id=%s place=%s trust=%.4f status=%s",
        row.id, place.id, trust, status_,
    )

    return ContributionResponse(
        id=row.id,
        place_id=place.id,
        place_name=place.name,
        trust_score=trust,
        vision_score=vision_result.score,
        nlp_score=nlp_score,
        visibility_status=status_,
        detected_features={
            cls: dets for cls, dets in vision_result.detections.items()
        },
    )
```

### 4. Training export router + CLI

Create `backend/app/services/training_export.py`:

```python
"""Export PUBLIC contributions into YOLO + RoBERTa-ready training datasets.

Layout produced under `--out-dir <dest>/<timestamp>/`:

  yolo/
    images/<contribution_id>.jpg
    labels/<contribution_id>.txt   # YOLO format: <cls> <cx> <cy> <w> <h>
    data.yaml                      # class names mapping
  roberta/
    train.csv                      # columns: text, label, trust_score, contribution_id
  manifest.json                    # cutoff, counts, hashes
"""
from __future__ import annotations

import csv
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contribution, TrainingExport

log = logging.getLogger(__name__)

_CLASS_MAP = {"ramp": 0, "stairs": 1, "steps": 2, "handrail": 3}


async def export_training_dataset(
    session: AsyncSession,
    *,
    out_dir: Path,
    started_at: datetime,
    ended_at: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> TrainingExport:
    ended_at = ended_at or datetime.now(timezone.utc)

    stmt = (
        select(Contribution)
        .where(Contribution.visibility_status == "PUBLIC")
        .where(Contribution.created_at >= started_at)
        .where(Contribution.created_at <= ended_at)
        .order_by(Contribution.created_at.asc())
    )
    rows = list((await session.execute(stmt)).scalars().all())

    stamp = ended_at.strftime("%Y%m%dT%H%M%S")
    dest = out_dir / stamp
    yolo_img = dest / "yolo" / "images"
    yolo_lab = dest / "yolo" / "labels"
    rob_dir = dest / "roberta"
    for d in (yolo_img, yolo_lab, rob_dir):
        d.mkdir(parents=True, exist_ok=True)

    yolo_count = 0
    roberta_rows = []

    for c in rows:
        # YOLO image + label
        src_img = Path(c.image_path)
        if src_img.exists():
            dst_img = yolo_img / f"{c.id}{src_img.suffix}"
            shutil.copy2(src_img, dst_img)
            label_path = yolo_lab / f"{c.id}.txt"
            with label_path.open("w") as f:
                for cls_name, dets in (c.detected_features or {}).items():
                    cls_idx = _CLASS_MAP.get(cls_name)
                    if cls_idx is None:
                        continue
                    for d in dets:
                        x1, y1, x2, y2 = d["bbox"]
                        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                        w, h = max(x2 - x1, 1e-6), max(y2 - y1, 1e-6)
                        f.write(f"{cls_idx} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
            yolo_count += 1
        # RoBERTa row (label = 1 since it's a verified PUBLIC review)
        roberta_rows.append({
            "text": c.text_note,
            "label": 1,
            "trust_score": c.trust_score,
            "contribution_id": str(c.id),
        })

    # data.yaml
    (dest / "yolo" / "data.yaml").write_text(
        "path: " + str(dest / "yolo") + "\n"
        "train: images\n"
        "val: images\n"
        "names:\n"
        "  0: ramp\n"
        "  1: stairs\n"
        "  2: steps\n"
        "  3: handrail\n"
    )

    csv_path = rob_dir / "train.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "trust_score", "contribution_id"])
        writer.writeheader()
        writer.writerows(roberta_rows)

    manifest = {
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "contribution_count": len(rows),
        "yolo_image_count": yolo_count,
        "roberta_row_count": len(roberta_rows),
        "notes": notes or "",
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2))

    record = TrainingExport(
        export_path=str(dest),
        cutoff_started_at=started_at,
        cutoff_ended_at=ended_at,
        contribution_count=len(rows),
        yolo_image_count=yolo_count,
        roberta_row_count=len(roberta_rows),
        notes=notes,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    log.info("training.export id=%s rows=%d dest=%s", record.id, len(rows), dest)
    return record
```

Create `backend/app/api/routers/training.py`:

```python
"""POST /api/v1/training/export — operator endpoint to cut a new dataset."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.services.training_export import export_training_dataset


router = APIRouter(prefix="/api/v1/training", tags=["training"])


class ExportRequest(BaseModel):
    started_at: datetime
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None
    out_dir: Optional[str] = None


class ExportResponse(BaseModel):
    id: UUID
    export_path: str
    contribution_count: int
    yolo_image_count: int
    roberta_row_count: int


@router.post("/export", response_model=ExportResponse)
async def export(
    body: ExportRequest,
    x_admin_token: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ExportResponse:
    expected = getattr(settings, "admin_token", None) or ""
    if not expected or x_admin_token != expected:
        raise HTTPException(401, "Admin token required")

    out_dir = Path(body.out_dir) if body.out_dir else Path("backend/training_exports")
    rec = await export_training_dataset(
        session,
        out_dir=out_dir,
        started_at=body.started_at,
        ended_at=body.ended_at,
        notes=body.notes,
    )
    return ExportResponse(
        id=rec.id,
        export_path=rec.export_path,
        contribution_count=rec.contribution_count,
        yolo_image_count=rec.yolo_image_count,
        roberta_row_count=rec.roberta_row_count,
    )
```

Add `admin_token: str = Field(default="", alias="ADMIN_TOKEN")` to `Settings`.
And register the router in `main.py`:

```python
from app.api.routers.training import router as training_router
app.include_router(training_router)
```

### 5. CLI for offline export

Create `backend/app/cli/training_export.py`:

```python
"""CLI: python -m app.cli.training_export --since 2025-01-01."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from app.db.session import SessionLocal
from app.services.training_export import export_training_dataset


def _parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _main(args: argparse.Namespace) -> None:
    async with SessionLocal() as session:
        rec = await export_training_dataset(
            session,
            out_dir=Path(args.out_dir),
            started_at=_parse_iso(args.since),
            ended_at=_parse_iso(args.until) if args.until else None,
            notes=args.notes,
        )
        print(f"export_id={rec.id} path={rec.export_path} rows={rec.contribution_count}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--since", required=True, help="ISO8601 start")
    p.add_argument("--until", help="ISO8601 end (default: now)")
    p.add_argument("--out-dir", default="backend/training_exports")
    p.add_argument("--notes")
    asyncio.run(_main(p.parse_args()))


if __name__ == "__main__":
    main()
```

### 6. Update `nearby` pin to expose `place_id`

Edit `backend/app/api/routers/nearby.py` `_to_pin` to include `place_id=row.place_id`.

---

## Acceptance criteria

- [ ] `POST /api/v1/verify` with only an EXIF-tagged image (no lat/lon) succeeds.
- [ ] `POST /api/v1/verify` with `google_place_id` succeeds even with no GPS at all.
- [ ] `POST /api/v1/verify` with no place_id, no GPS, no EXIF, no address returns 422.
- [ ] After two contributions at the same place, `places.contribution_count = 2` and `aggregate_trust` is the recency-weighted mean.
- [ ] `POST /api/v1/training/export` with `X-Admin-Token` header writes a directory tree containing `yolo/images/`, `yolo/labels/`, `yolo/data.yaml`, `roberta/train.csv`, and `manifest.json`.
- [ ] `python -m app.cli.training_export --since 2025-01-01` prints an export_id and writes the same tree.
- [ ] All existing tests still pass; new tests for resolver edge cases added.

## Smoke commands

```bash
# Submit with explicit place_id
PID=$(curl -s 'http://127.0.0.1:8000/api/v1/places/search?query=Phoenix+Marketcity+Bangalore' | jq -r '.[0].google_place_id')
curl -X POST http://127.0.0.1:8000/api/v1/verify \
  -F "image=@./backend/app/static/warmup.jpg" \
  -F "review=Wide ramp at the side entrance, no steps." \
  -F "rating=4" \
  -F "google_place_id=$PID" | jq

# Submit with EXIF-only photo
curl -X POST http://127.0.0.1:8000/api/v1/verify \
  -F "image=@/path/to/exif_geotagged.jpg" \
  -F "review=Steep ramp but accessible." \
  -F "rating=3" | jq

# Confirm aggregate updated
docker exec naviable-postgis psql -U naviable -d naviable -c \
  "SELECT name, contribution_count, public_count, aggregate_trust FROM places ORDER BY updated_at DESC LIMIT 3;"

# Cut a training export
ADMIN_TOKEN=devsecret python -m app.cli.training_export --since 2025-01-01 --notes "first cut"
ls backend/training_exports/*/
```

## Pitfalls

- The reverse-geocode in `_resolve_from_coords` adds one extra Google call
  per submit — at scale, cache by truncated lat/lon. The TTL cache from
  phase 02 already handles repeats within 60s.
- The denormalised `aggregate_trust` is updated **before commit**. If the
  recompute SQL throws, the contribution insert rolls back — desired.
- `recompute_place_aggregates` uses `place.id` (UUID) not `place_id` string —
  cast carefully.
- The training export copies image files; on a real deployment, store
  uploads in S3 and copy with `boto3` instead of `shutil`.
- The RoBERTa export currently labels every PUBLIC row as `1`. If you also
  want negative samples (LABEL_0 = generic accessibility-washing), seed the
  CSV from `accessibility_reviews.csv` already in the repo root.
