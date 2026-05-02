"""Pydantic v2 schemas for the contribution API."""
from __future__ import annotations
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class FeatureDetection(BaseModel):
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 normalised


class ContributionCreate(BaseModel):
    review: Annotated[str, StringConstraints(min_length=1, max_length=2000, strip_whitespace=True)]
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]
    rating: Annotated[int, Field(ge=1, le=5)]


class ContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    trust_score: float
    vision_score: float
    nlp_score: float
    visibility_status: Literal["PUBLIC", "CAVEAT", "HIDDEN"]
    detected_features: dict[str, list[FeatureDetection]]


class ContributionPin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    latitude: float
    longitude: float
    trust_score: float
    visibility_status: Literal["PUBLIC", "CAVEAT"]
    rating: int
    text_note: str
    image_url: str | None


class NearbyResponse(BaseModel):
    items: list[ContributionPin]
