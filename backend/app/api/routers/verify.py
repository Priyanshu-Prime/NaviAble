"""POST /api/v1/verify — submission + dual-AI trust scoring."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.uploads import validate_and_persist_upload
from app.db.models import Contribution
from app.db.session import get_session
from app.schemas.contribution import ContributionCreate, ContributionResponse
from app.services.fusion import assign_status, compute_trust_score
from app.services.nlp import NlpUnavailable
from app.services.vision import VisionUnavailable

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["verify"])


@router.post("/verify", response_model=ContributionResponse, status_code=201)
async def verify(
    request: Request,
    image: UploadFile = File(...),
    review: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    rating: int = Form(...),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ContributionResponse:
    # Edge validation via Pydantic
    payload = ContributionCreate(
        review=review,
        latitude=latitude,
        longitude=longitude,
        rating=rating,
    )

    # Save upload (raises 415/413/422 on failure)
    saved_path = await validate_and_persist_upload(image, settings=settings)

    vision_svc = request.app.state.vision
    nlp_svc = request.app.state.nlp

    # Run both AI services concurrently
    try:
        vision_result, nlp_score = await asyncio.gather(
            vision_svc.score(saved_path),
            nlp_svc.score(payload.review),
        )
    except VisionUnavailable as exc:
        log.error("vision.unavailable err=%s", exc)
        raise HTTPException(503, "Vision service unavailable") from exc
    except NlpUnavailable as exc:
        log.error("nlp.unavailable err=%s", exc)
        raise HTTPException(503, "NLP service unavailable") from exc

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
        detected_features={
            cls: [d.model_dump() for d in dets]
            for cls, dets in vision_result.detections.items()
        },
    )
    try:
        session.add(row)
        await session.commit()
        await session.refresh(row)
    except Exception as exc:
        # Clean up orphan upload file on DB failure
        await asyncio.to_thread(saved_path.unlink, missing_ok=True)
        log.error("db.write_failed err=%s", exc)
        raise HTTPException(503, "Could not persist contribution") from exc

    log.info(
        "verify.ok id=%s trust=%.4f status=%s",
        row.id, trust, status_,
    )

    return ContributionResponse(
        id=row.id,
        trust_score=trust,
        vision_score=vision_result.score,
        nlp_score=nlp_score,
        visibility_status=status_,
        detected_features={
            cls: dets for cls, dets in vision_result.detections.items()
        },
    )
