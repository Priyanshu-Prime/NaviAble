"""Pydantic schemas for the places API."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlaceSummary(BaseModel):
    """Map-marker-sized payload — sent in lists."""

    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID]  # null for places we've never stored
    google_place_id: str
    name: str
    formatted_address: Optional[str]
    latitude: float
    longitude: float
    google_types: List[str] = Field(default_factory=list)
    aggregate_trust: float  # 0.0 if no public contributions
    public_count: int  # 0 if none
    contribution_count: int
    has_data: bool  # has at least 1 PUBLIC contribution


class PlaceDetail(PlaceSummary):
    """Place page payload — includes most-recent contributions."""

    contributions: List["ContributionPin"] = Field(default_factory=list)


class PlaceAutocomplete(BaseModel):
    """Autocomplete result from Google Places."""

    google_place_id: str
    description: str  # "Starbucks, MG Road, Bangalore"
    main_text: str
    secondary_text: Optional[str]


from app.schemas.contribution import ContributionPin  # noqa: E402  (forward ref)

PlaceDetail.model_rebuild()
