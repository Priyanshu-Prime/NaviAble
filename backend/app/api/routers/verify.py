"""
FastAPI router for the NaviAble dual-AI verification endpoint.

Endpoint: POST /api/v1/verify

Accepts a multipart/form-data request containing:
- ``text_review``  : str   — the user's written review.
- ``location_id``  : str   — UUID of the location being reviewed.
- ``image``        : File  — JPEG or PNG of the physical environment.

The handler fans out to both ML services **concurrently** using
``asyncio.gather``, with each blocking call wrapped in
``asyncio.to_thread`` so the async event loop remains unblocked.
The final NaviAble Trust Score is calculated as:

    trust_score = 0.60 × (vision confidence) + 0.40 × (nlp confidence)

Vision confidence is the mean detection confidence of all features found
by YOLO (or 0.0 when no features are detected).
NLP confidence is the Class-1 probability returned by RoBERTa.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from app.schemas.verify import (
    DetectedFeature,
    NLPAnalysis,
    VerificationData,
    VerificationResponse,
    VisionAnalysis,
)
from app.services.ml import RobertaNLPService, YoloVisionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Verification"])

# Maximum accepted image size: 10 MB
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


@router.post(
    "/verify",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Dual-AI Accessibility Verification",
    description=(
        "Accepts a user-submitted text review and an image of the location. "
        "Runs both YOLOv11 (vision) and RoBERTa (NLP) inference concurrently "
        "and returns a composite NaviAble Trust Score."
    ),
)
async def verify_accessibility(
    request: Request,
    text_review: str = Form(..., description="User's written accessibility review."),
    location_id: UUID = Form(..., description="UUID of the location being reviewed."),
    image: UploadFile = File(..., description="JPEG or PNG image of the location."),
) -> VerificationResponse:
    """Run the NaviAble Dual-AI verification pipeline.

    Parameters
    ----------
    request : Request
        FastAPI request object — provides access to ``app.state`` where
        the ML service singletons are stored.
    text_review : str
        Raw review text from the multipart form field ``text_review``.
    location_id : UUID
        UUID identifying the location being reviewed.
    image : UploadFile
        Uploaded image file (JPEG or PNG).

    Returns
    -------
    VerificationResponse
        Structured JSON response matching the API contract in
        ``.agent/architecture/API_CONTRACTS.md``.

    Raises
    ------
    HTTPException 400
        If the uploaded file is not a supported image MIME type or exceeds
        the 10 MB size limit.
    HTTPException 503
        If one or more ML services are unavailable (e.g. weights not loaded).
    """
    # ------------------------------------------------------------------
    # Validate uploaded file
    # ------------------------------------------------------------------
    if image.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{image.content_type}'. Use image/jpeg or image/png.",
        )

    image_bytes = await image.read()
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image exceeds maximum allowed size of {_MAX_IMAGE_BYTES // (1024 * 1024)} MB.",
        )

    # ------------------------------------------------------------------
    # Retrieve service singletons from app state
    # ------------------------------------------------------------------
    yolo: YoloVisionService = request.app.state.yolo_service
    roberta: RobertaNLPService = request.app.state.roberta_service

    # ------------------------------------------------------------------
    # Run both models concurrently without blocking the event loop.
    # asyncio.to_thread() dispatches the synchronous (blocking) predict /
    # classify calls to a thread-pool worker, returning an awaitable.
    # asyncio.gather() runs both awaitables in parallel.
    # ------------------------------------------------------------------
    try:
        vision_raw, nlp_raw = await asyncio.gather(
            asyncio.to_thread(yolo.predict, image_bytes),
            asyncio.to_thread(roberta.classify, text_review),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("ML inference failed for location_id=%s: %s", location_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML inference service temporarily unavailable.",
        ) from exc

    # ------------------------------------------------------------------
    # Build validated Pydantic response objects
    # ------------------------------------------------------------------
    features = [
        DetectedFeature.model_validate(
            {
                "class": f["class"],
                "confidence": f["confidence"],
                "bbox": f["bbox"],
            }
        )
        for f in vision_raw.get("features", [])
    ]

    vision_analysis = VisionAnalysis(
        objects_detected=vision_raw.get("objects_detected", 0),
        features=features,
    )

    nlp_analysis = NLPAnalysis(
        is_genuine=nlp_raw["is_genuine"],
        confidence=nlp_raw["confidence"],
        label=nlp_raw["label"],
    )

    # ------------------------------------------------------------------
    # Calculate NaviAble Trust Score:  60 % vision + 40 % NLP
    # Vision confidence = mean confidence of all detected features
    # (falls back to 0.0 when no features were found)
    # ------------------------------------------------------------------
    vision_conf = (
        sum(f.confidence for f in features) / len(features)
        if features
        else 0.0
    )
    nlp_conf = nlp_analysis.confidence
    trust_score = round(0.60 * vision_conf + 0.40 * nlp_conf, 4)

    return VerificationResponse(
        status="success",
        data=VerificationData(
            nlp_analysis=nlp_analysis,
            vision_analysis=vision_analysis,
            naviable_trust_score=trust_score,
        ),
    )
