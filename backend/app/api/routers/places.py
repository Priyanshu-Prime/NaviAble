"""Place-centric discovery endpoints (Google Places + DB merge)."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_google_places
from app.api.routers.nearby import _compose_image_url
from app.core.config import Settings, get_settings
from app.db.models import Contribution, Place
from app.db.queries import (
    find_nearby_places,
    find_reviewed_places,
    get_all_reviewed_places,
    search_places_by_name,
    upsert_place,
)
from app.db.session import get_session
from app.schemas.contribution import ContributionPin
from app.schemas.place import PlaceAutocomplete, PlaceDetail, PlaceSummary
from app.services.google_places import GooglePlacesService, GooglePlacesUnavailable

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/places", tags=["places"])


def _row_to_summary(row: Place, google_doc: Optional[dict] = None) -> PlaceSummary:
    from geoalchemy2.shape import to_shape

    pt = to_shape(row.location)
    return PlaceSummary(
        id=row.id,
        google_place_id=row.google_place_id,
        name=row.name,
        formatted_address=row.formatted_address,
        latitude=round(pt.y, 7),
        longitude=round(pt.x, 7),
        google_types=row.google_types or [],
        aggregate_trust=row.aggregate_trust,
        public_count=row.public_count,
        contribution_count=row.contribution_count,
        has_data=row.public_count > 0,
    )


def _google_to_summary(g: dict) -> PlaceSummary:
    loc = g.get("geometry", {}).get("location", {})
    return PlaceSummary(
        id=None,
        google_place_id=g["place_id"],
        name=g.get("name", ""),
        formatted_address=g.get("vicinity") or g.get("formatted_address"),
        latitude=float(loc.get("lat", 0.0)),
        longitude=float(loc.get("lng", 0.0)),
        google_types=g.get("types", []),
        aggregate_trust=0.0,
        public_count=0,
        contribution_count=0,
        has_data=False,
    )


@router.get("/reviewed/nearby", response_model=list[PlaceSummary])
async def reviewed_nearby(
    response: Response,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_m: int = Query(5000, gt=0),
    session: AsyncSession = Depends(get_session),
) -> list[PlaceSummary]:
    """Get places with reviews (public contributions) within radius.

    Returns only places that have been reviewed by the community, sorted by distance.
    Default radius is 5km.
    """
    radius_m = min(radius_m, 25000)
    places = await find_reviewed_places(
        session,
        lat=latitude,
        lon=longitude,
        radius_m=radius_m,
        limit=200,
    )
    response.headers["Cache-Control"] = "public, max-age=15"
    return [_row_to_summary(p) for p in places]


@router.get("/nearby", response_model=list[PlaceSummary])
async def nearby(
    response: Response,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_m: int = Query(800, gt=0),
    keyword: Optional[str] = Query(None, max_length=120),
    place_type: Optional[str] = Query(None, max_length=64),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    google: GooglePlacesService = Depends(get_google_places),
) -> list[PlaceSummary]:
    """Merged Google Nearby + DB places.

    Strategy:
      1. Ask Google for places near (lat,lon).
      2. Look up each `place_id` in our DB; if found, overlay its trust data.
      3. Also include DB places that Google didn't return (rare, but possible
         when a contribution exists for a place outside Google's response).
    """
    radius_m = min(radius_m, settings.nearby_max_radius_m)

    try:
        google_results, db_places = await asyncio.gather(
            google.nearby_search(
                lat=latitude,
                lon=longitude,
                radius_m=radius_m,
                keyword=keyword,
                place_type=place_type,
            ),
            find_nearby_places(
                session,
                lat=latitude,
                lon=longitude,
                radius_m=radius_m,
                limit=200,
            ),
        )
    except GooglePlacesUnavailable as exc:
        raise HTTPException(503, "Place search unavailable") from exc

    db_by_gid = {p.google_place_id: p for p in db_places}
    out: list[PlaceSummary] = []

    for g in google_results:
        gid = g.get("place_id")
        if not gid:
            continue
        db_row = db_by_gid.pop(gid, None)
        if db_row is not None:
            summary = _row_to_summary(db_row)
        else:
            summary = _google_to_summary(g)
        out.append(summary)

    # Tail-include DB places Google didn't surface
    for leftover in db_by_gid.values():
        out.append(_row_to_summary(leftover))

    response.headers["Cache-Control"] = "public, max-age=15"
    return out


@router.get("/search/db", response_model=list[PlaceSummary])
async def search_database(
    query: str = Query(..., min_length=1, max_length=120),
    session: AsyncSession = Depends(get_session),
) -> list[PlaceSummary]:
    """Search places in the database by name.

    This endpoint searches the local database for places that match the query.
    Use this when a place is not available in Google Places.
    """
    results = await search_places_by_name(session, query=query, limit=20)
    return [_row_to_summary(r) for r in results]


@router.get("/search", response_model=list[PlaceAutocomplete])
async def search(
    query: str = Query(..., min_length=1, max_length=120),
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    google: GooglePlacesService = Depends(get_google_places),
) -> list[PlaceAutocomplete]:
    try:
        preds = await google.autocomplete(query=query, lat=latitude, lon=longitude)
    except GooglePlacesUnavailable as exc:
        raise HTTPException(503, "Place search unavailable") from exc

    return [
        PlaceAutocomplete(
            google_place_id=p["place_id"],
            description=p.get("description", ""),
            main_text=p.get("structured_formatting", {}).get("main_text", ""),
            secondary_text=p.get("structured_formatting", {}).get("secondary_text"),
        )
        for p in preds
    ]


@router.get("/{place_identifier}", response_model=PlaceDetail)
async def detail(
    place_identifier: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    google: GooglePlacesService = Depends(get_google_places),
) -> PlaceDetail:
    """Full place page: aggregate trust + recent contributions.

    Supports two modes:
    1. Google Place ID (starts with "ChIJ" or similar) - fetches from Google, upserts to DB
    2. Place name - searches database for exact/fuzzy matches

    Priority: Database first (local data), then Google Places API as fallback.
    """
    # First, try to fetch by google_place_id if it looks like one
    place = (await session.execute(
        select(Place).where(Place.google_place_id == place_identifier)
    )).scalar_one_or_none()

    # If not found by google_place_id, try searching database by name first
    if place is None:
        search_results = await search_places_by_name(
            session, query=place_identifier, limit=1
        )
        if search_results:
            place = search_results[0]

    # If still not found, try Google Places API as fallback
    if place is None:
        # Try Google Places API if it looks like a valid Google Place ID
        # Google IDs typically start with "ChIJ" or are long alphanumeric strings
        if place_identifier.startswith("ChIJ") or len(place_identifier) > 20:
            try:
                details = await google.details(place_id=place_identifier)
                if details:
                    loc = details["geometry"]["location"]
                    place = await upsert_place(
                        session,
                        google_place_id=place_identifier,
                        name=details.get("name", ""),
                        formatted_address=details.get("formatted_address"),
                        lat=float(loc["lat"]),
                        lon=float(loc["lng"]),
                        google_types=details.get("types", []),
                    )
                    await session.commit()
            except GooglePlacesUnavailable:
                pass

    if place is None:
        raise HTTPException(404, "Place not found in database or Google Places")

    # Pull recent public/caveat contributions
    crows = (
        await session.execute(
            select(Contribution)
            .where(Contribution.place_id == place.id)
            .where(Contribution.visibility_status.in_(["PUBLIC", "CAVEAT"]))
            .order_by(Contribution.created_at.desc())
            .limit(50)
        )
    ).scalars().all()

    from geoalchemy2.shape import to_shape

    def _pin(c: Contribution) -> ContributionPin:
        pt = to_shape(c.location)
        return ContributionPin(
            id=c.id,
            place_id=c.place_id,
            latitude=round(pt.y, 7),
            longitude=round(pt.x, 7),
            trust_score=c.trust_score,
            visibility_status=c.visibility_status,
            rating=c.rating,
            text_note=c.text_note,
            image_url=_compose_image_url(c.image_path, settings),
        )

    summary = _row_to_summary(place)
    return PlaceDetail(
        **summary.model_dump(),
        contributions=[_pin(c) for c in crows],
    )
