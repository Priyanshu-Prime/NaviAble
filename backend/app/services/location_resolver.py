"""Resolve a contribution's location from one of: place_id / coords / EXIF / address.

Chain priority (most authoritative first):
  1. `google_place_id` — explicit user choice. Always wins.
  2. `(latitude, longitude)` from form fields — device GPS at submit time.
  3. EXIF GPS embedded in the uploaded photo.
  4. Reverse-geocode of `address` string.

Returns the resolved Place row (upserted) and effective (lat, lon).
Raises HTTPException(422) if every signal is missing or invalid.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Place
from app.db.queries import upsert_place
from app.services.exif import extract_gps
from app.services.google_places import GooglePlacesService, GooglePlacesUnavailable

log = logging.getLogger(__name__)


async def resolve_place(
    session: AsyncSession,
    google: GooglePlacesService,
    *,
    google_place_id: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    address: Optional[str],
    image_path: Path,
    typed_address: Optional[str] = None,
) -> Tuple[Place, float, float]:
    """Resolve location via priority chain, return (Place, lat, lon)."""
    # 1. explicit place id
    if google_place_id:
        existing = (
            await session.execute(
                select(Place).where(Place.google_place_id == google_place_id)
            )
        ).scalar_one_or_none()
        if existing:
            from geoalchemy2.shape import to_shape

            pt = to_shape(existing.location)
            return existing, pt.y, pt.x
        try:
            details = await google.details(place_id=google_place_id)
        except GooglePlacesUnavailable as exc:
            raise HTTPException(503, "Place lookup unavailable") from exc
        if not details:
            raise HTTPException(422, "Unknown google_place_id")
        loc = details["geometry"]["location"]
        place = await upsert_place(
            session,
            google_place_id=google_place_id,
            name=details.get("name", ""),
            formatted_address=details.get("formatted_address"),
            lat=float(loc["lat"]),
            lon=float(loc["lng"]),
            google_types=details.get("types", []),
        )
        return place, float(loc["lat"]), float(loc["lng"])

    # 2. raw coordinates
    if latitude is not None and longitude is not None:
        return await _resolve_from_coords(
            session, google, latitude, longitude, typed_address=typed_address
        )

    # 3. EXIF GPS
    gps = extract_gps(image_path)
    if gps is not None:
        log.info("verify.exif_gps lat=%s lon=%s", *gps)
        return await _resolve_from_coords(
            session, google, gps[0], gps[1], typed_address=typed_address
        )

    # 4. address geocode
    if address:
        try:
            geo = await google.geocode_address(address=address)
        except GooglePlacesUnavailable as exc:
            raise HTTPException(503, "Geocoding unavailable") from exc
        if geo and "geometry" in geo:
            loc = geo["geometry"]["location"]
            return await _resolve_from_coords(
                session, google, float(loc["lat"]), float(loc["lng"]),
                typed_address=typed_address
            )

    raise HTTPException(
        422,
        "Could not determine location: provide google_place_id, "
        "(latitude,longitude), an address, or upload a geo-tagged photo.",
    )


async def _resolve_from_coords(
    session: AsyncSession,
    google: GooglePlacesService,
    lat: float,
    lon: float,
    typed_address: Optional[str] = None,
) -> Tuple[Place, float, float]:
    """Reverse-geocode (lat,lon) → place_id → upsert."""
    try:
        geo = await google.reverse_geocode(lat=lat, lon=lon)
    except GooglePlacesUnavailable as exc:
        raise HTTPException(503, "Geocoding unavailable") from exc

    if not geo:
        raise HTTPException(422, "Could not match coordinates to a Google place")
    pid = geo.get("place_id")
    if not pid:
        raise HTTPException(422, "Reverse-geocode returned no place_id")
    types = geo.get("types", [])

    # Use typed_address if provided (user's original search), otherwise use Google's result
    formatted_addr = typed_address or geo.get("formatted_address")
    name = (typed_address or geo.get("formatted_address", "Unnamed place")).split(",")[0]

    place = await upsert_place(
        session,
        google_place_id=pid,
        name=name,
        formatted_address=formatted_addr,
        lat=lat,
        lon=lon,
        google_types=types,
    )
    return place, lat, lon
