"""
Pydantic v2 response schemas for the NaviAble verification API.

These models strictly mirror the JSON contract defined in
.agent/architecture/API_CONTRACTS.md and are used both for
FastAPI response serialisation and for test assertion validation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class DetectedFeature(BaseModel):
    """A single accessibility feature detected by the YOLO vision model."""

    model_config = ConfigDict(frozen=True)

    class_name: str = Field(alias="class", description="Human-readable feature class (e.g. 'ramp', 'handrail').")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence in [0, 1].")
    bbox: list[int] = Field(min_length=4, max_length=4, description="Bounding box [x1, y1, x2, y2] in pixels.")


class VisionAnalysis(BaseModel):
    """Aggregated output from the YOLOv11 vision inference pipeline."""

    model_config = ConfigDict(frozen=True)

    objects_detected: int = Field(ge=0, description="Total number of accessibility features detected above threshold.")
    features: list[DetectedFeature] = Field(description="List of individual detected features.")


class NLPAnalysis(BaseModel):
    """Output from the RoBERTa NLP Integrity Engine."""

    model_config = ConfigDict(frozen=True)

    is_genuine: bool = Field(description="True if the review contains genuine physical accessibility details.")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence that the review is genuine.")
    label: str = Field(description="Human-readable classification label.")


class VerificationData(BaseModel):
    """Combined dual-AI verification results for a single submission."""

    model_config = ConfigDict(frozen=True)

    nlp_analysis: NLPAnalysis
    vision_analysis: VisionAnalysis
    naviable_trust_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Composite trust score: 60 % vision confidence + 40 % NLP confidence, "
            "normalised to [0, 1]. Reflects the overall physical accessibility evidence."
        ),
    )


class VerificationResponse(BaseModel):
    """Top-level API response envelope for POST /api/v1/verify."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(description="'success' on a valid inference run.")
    data: VerificationData
