"""GET /api/v1/contributions/nearby — spatial discovery."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import Contribution
from app.db.queries import find_nearby
from app.db.session import get_session
from app.schemas.contribution import ContributionPin, NearbyResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["discovery"])


def _compose_image_url(image_path: str, settings: Settings) -> Optional[str]:
    if not image_path:
        return None
    filename = Path(image_path).name
    base = settings.public_base_url.rstrip("/")
    prefix = settings.static_prefix.rstrip("/")
    return f"{base}{prefix}/{filename}"


def _to_pin(row: Contribution, settings: Settings) -> ContributionPin:
    from geoalchemy2.shape import to_shape
    point = to_shape(row.location)
    return ContributionPin(
        id=row.id,
        place_id=row.place_id,
        latitude=round(point.y, 7),
        longitude=round(point.x, 7),
        trust_score=row.trust_score,
        visibility_status=row.visibility_status,
        rating=row.rating,
        text_note=row.text_note,
        image_url=_compose_image_url(row.image_path, settings),
    )


@router.get("/contributions/nearby", response_model=NearbyResponse)
async def nearby(
    response: Response,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(..., gt=0, le=10_000),
    include_caveat: bool = Query(True),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> NearbyResponse:
    rows = await find_nearby(
        session,
        lat=latitude,
        lon=longitude,
        radius_m=radius_m,
        include_caveat=include_caveat,
        limit=200,
    )
    response.headers["Cache-Control"] = "public, max-age=15"
    return NearbyResponse(items=[_to_pin(r, settings) for r in rows])
