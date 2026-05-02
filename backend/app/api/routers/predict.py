"""FastAPI router for YOLOv10 image upload and accessibility prediction."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Prediction"])

# Maximum image size: 10 MB
_MAX_IMAGE_BYTES = 10 * 1024 * 1024

# Uploads directory
UPLOADS_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
(UPLOADS_DIR / "images").mkdir(exist_ok=True)
(UPLOADS_DIR / "predictions").mkdir(exist_ok=True)
(UPLOADS_DIR / "reviews").mkdir(exist_ok=True)


@router.post(
    "/predict",
    status_code=status.HTTP_200_OK,
    summary="Predict Accessibility Features in Image",
    description=(
        "Upload an image of a public space to detect accessibility features "
        "(ramps and stairs) using the trained YOLOv10 model."
    ),
)
async def predict_accessibility_features(
    request: Request,
    image: UploadFile = File(..., description="JPEG or PNG image of a location."),
) -> dict[str, Any]:
    """Predict accessibility features in an uploaded image.

    Parameters
    ----------
    request : Request
        FastAPI request object with ML service singletons.
    image : UploadFile
        Uploaded image file.

    Returns
    -------
    dict
        Response containing:
        - prediction_id: unique ID for this prediction
        - features: list of detected features (ramps, stairs)
        - image_url: path to saved image
        - created_at: timestamp

    Raises
    ------
    HTTPException 400
        If image type is unsupported or exceeds size limit.
    HTTPException 503
        If ML service is unavailable.
    """
    # Validate image type
    if image.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{image.content_type}'. Use JPEG or PNG.",
        )

    # Read and validate image bytes
    image_bytes = await image.read()
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds maximum size of {_MAX_IMAGE_BYTES / 1e6:.1f} MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Get ML service
    yolo_v10_service = getattr(request.app.state, "yolo_v10_service", None)
    if yolo_v10_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLOv10 service not available.",
        )

    # Run prediction in thread pool (blocking operation)
    try:
        result = await asyncio.to_thread(yolo_v10_service.predict, image_bytes)
    except Exception as exc:
        logger.error("Prediction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed. Please try again.",
        ) from exc

    # Generate unique IDs and timestamps
    prediction_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    date_dir = datetime.utcnow().strftime("%Y-%m-%d")

    # Save image
    image_dir = UPLOADS_DIR / "images" / date_dir
    image_dir.mkdir(parents=True, exist_ok=True)
    image_filename = f"{prediction_id}_{image.filename}"
    image_path = image_dir / image_filename

    with open(image_path, "wb") as f:
        f.write(image_bytes)

    # Save prediction results
    prediction_dir = UPLOADS_DIR / "predictions" / date_dir
    prediction_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = prediction_dir / f"{prediction_id}.json"

    prediction_data = {
        "prediction_id": prediction_id,
        "timestamp": timestamp,
        "image_filename": image_filename,
        "image_path": str(image_path.relative_to(UPLOADS_DIR.parent)),
        "features": result.get("features", []),
        "objects_detected": result.get("objects_detected", 0),
    }

    with open(prediction_path, "w") as f:
        json.dump(prediction_data, f, indent=2)

    logger.info("Prediction saved: %s with %d features", prediction_id, result.get("objects_detected", 0))

    return {
        "prediction_id": prediction_id,
        "timestamp": timestamp,
        "features": result.get("features", []),
        "objects_detected": result.get("objects_detected", 0),
        "image_url": f"/uploads/images/{date_dir}/{image_filename}",
    }


@router.post(
    "/submit-review",
    status_code=status.HTTP_201_CREATED,
    summary="Submit Accessibility Review with Predictions",
    description=(
        "Submit a complete accessibility review including location details, "
        "user review text, and predicted features from the image."
    ),
)
async def submit_accessibility_review(
    request: Request,
    prediction_id: str = Form(..., description="ID of the prediction to associate with this review."),
    location_name: str = Form(..., description="Name of the location being reviewed."),
    location_type: str = Form(..., description="Type of location (e.g., 'entrance', 'parking', 'sidewalk')."),
    review_text: str = Form(..., description="User's accessibility review."),
    accessibility_rating: int = Form(..., ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)."),
    detected_features: str = Form(..., description="JSON string of detected features from prediction."),
) -> dict[str, Any]:
    """Submit a complete accessibility review with predictions.

    Parameters
    ----------
    prediction_id : str
        ID of the associated YOLOv10 prediction.
    location_name : str
        Name/description of the location.
    location_type : str
        Category of location.
    review_text : str
        User's review text.
    accessibility_rating : int
        Accessibility rating (1-5).
    detected_features : str
        JSON string of features detected by YOLOv10.

    Returns
    -------
    dict
        Confirmation with review ID and storage info.
    """
    review_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    date_dir = datetime.utcnow().strftime("%Y-%m-%d")

    # Parse detected features
    try:
        features = json.loads(detected_features)
    except json.JSONDecodeError:
        features = []

    # Save review
    review_dir = UPLOADS_DIR / "reviews" / date_dir
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"{review_id}.json"

    review_data = {
        "review_id": review_id,
        "prediction_id": prediction_id,
        "timestamp": timestamp,
        "location": {
            "name": location_name,
            "type": location_type,
        },
        "review_text": review_text,
        "accessibility_rating": accessibility_rating,
        "detected_features": features,
    }

    with open(review_path, "w") as f:
        json.dump(review_data, f, indent=2)

    logger.info("Review submitted: %s for location %s", review_id, location_name)

    return {
        "review_id": review_id,
        "prediction_id": prediction_id,
        "status": "submitted",
        "timestamp": timestamp,
        "message": f"Review for '{location_name}' submitted successfully.",
    }


@router.get(
    "/prediction/{prediction_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Prediction Details",
)
async def get_prediction(prediction_id: str) -> dict[str, Any]:
    """Retrieve details of a previous prediction by ID."""
    # Search for prediction file
    for date_dir in (UPLOADS_DIR / "predictions").glob("*"):
        prediction_path = date_dir / f"{prediction_id}.json"
        if prediction_path.exists():
            with open(prediction_path) as f:
                return json.load(f)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Prediction with ID '{prediction_id}' not found.",
    )


@router.get(
    "/review/{review_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Review Details",
)
async def get_review(review_id: str) -> dict[str, Any]:
    """Retrieve details of a previous review by ID."""
    # Search for review file
    for date_dir in (UPLOADS_DIR / "reviews").glob("*"):
        review_path = date_dir / f"{review_id}.json"
        if review_path.exists():
            with open(review_path) as f:
                return json.load(f)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Review with ID '{review_id}' not found.",
    )
