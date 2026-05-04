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
        typed_address=payload.address,
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
        image_phash=str(vision_result.image_phash),
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
        row.id,
        place.id,
        trust,
        status_,
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
