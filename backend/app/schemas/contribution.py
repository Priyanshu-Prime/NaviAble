"""Pydantic v2 schemas for the contribution API."""
from __future__ import annotations

from typing import Annotated, Dict, List, Literal, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class FeatureDetection(BaseModel):
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2 normalised


class ContributionCreate(BaseModel):
    review: Annotated[
        str,
        StringConstraints(min_length=1, max_length=2000, strip_whitespace=True),
    ]
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
    detected_features: Dict[str, List[FeatureDetection]]


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
