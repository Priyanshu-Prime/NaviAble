# Phase 02 — Backend: Google Places integration + EXIF + new endpoints

**Status:** not started
**Depends on:** phase 01 (places + contributions.place_id + training_exports)
**Affects:** `backend/app/services/`, `backend/app/api/routers/`, `backend/app/schemas/`, `backend/app/core/config.py`, `backend/.env*`, `backend/requirements.txt`

## Goal

Add three new endpoints — `/places/nearby`, `/places/search`,
`/places/{place_id}` — backed by a server-side Google Places client (so the
powerful API key never leaves the server). Add an EXIF GPS extractor so
photo uploads can self-locate, and a reverse-geocoding helper for the
"address fallback" path. The frontend will call **only** our endpoints, never
Google directly.

We keep `/api/v1/contributions/nearby` because the map view's "raw pin" toggle
(phase 05) still needs it.

---

## Deliverables

### 1. Add dependencies

`backend/requirements.txt` — append:

```text
# ──── HTTP for Google Places ────
httpx>=0.27.0   # already present
tenacity>=9.0.0
cachetools>=5.3.0
```

`tenacity` retries the Places call on transient 5xx without hand-rolling
backoff. `cachetools` powers an in-process TTL cache so we don't pay for
identical queries within 60s.

### 2. Extend settings

Edit `backend/app/core/config.py`. Add fields:

```python
# ── Google Places (server-side key) ─────────────────────────────────────
google_places_api_key: str = Field(default="", alias="GOOGLE_PLACES_API_KEY")
google_places_base_url: str = Field(
    default="https://maps.googleapis.com/maps/api/place",
)
google_places_timeout_s: float = Field(default=8.0)
google_places_cache_ttl_s: int = Field(default=60)

# ── Discovery / aggregation ─────────────────────────────────────────────
nearby_default_radius_m: int = Field(default=800)
nearby_max_radius_m: int = Field(default=10_000)
trust_recency_half_life_days: int = Field(default=180)
```

Ship `.env.example` with:

```bash
# ── Google Places (server-side) ───────────────────────────────────────
# Restrict this key to "Places API" + "Geocoding API" only.
# It is NEVER embedded in the mobile app — only the Maps SDK key is.
GOOGLE_PLACES_API_KEY=
```

### 3. Google Places service

Create `backend/app/services/google_places.py`:

```python
"""Server-side Google Places client (Nearby + Autocomplete + Details + Geocoding)."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from cachetools import TTLCache
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings

log = logging.getLogger(__name__)


class GooglePlacesUnavailable(RuntimeError):
    """Google Places API is unreachable / rate-limited / mis-keyed."""


class GooglePlacesService:
    """Thin async wrapper around Places + Geocoding REST APIs.

    Cached at the request-key granularity for `cache_ttl_s` seconds. Cache
    keys are tuples of (endpoint, sorted-kwargs) — small footprint, eviction
    by TTL handles freshness. NOT a CDN — this only deduplicates rapid-fire
    repeats from the same backend instance.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=settings.google_places_timeout_s,
            base_url=settings.google_places_base_url,
        )
        self._cache: TTLCache = TTLCache(
            maxsize=512, ttl=settings.google_places_cache_ttl_s,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.2, max=2.0),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._settings.google_places_api_key:
            raise GooglePlacesUnavailable(
                "GOOGLE_PLACES_API_KEY not configured"
            )
        params = {**params, "key": self._settings.google_places_api_key}
        cache_key = (path, tuple(sorted(params.items())))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = await self._client.get(path, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.error("google_places.http_error path=%s err=%s", path, exc)
            raise GooglePlacesUnavailable(str(exc)) from exc

        data = resp.json()
        # Google's REST API returns 200 with status="ZERO_RESULTS" / "OVER_QUERY_LIMIT" etc.
        status = data.get("status")
        if status == "OVER_QUERY_LIMIT":
            raise GooglePlacesUnavailable("Quota exceeded")
        if status not in ("OK", "ZERO_RESULTS"):
            log.error("google_places.bad_status path=%s status=%s", path, status)
            raise GooglePlacesUnavailable(f"Google status={status}")

        self._cache[cache_key] = data
        return data

    # ── Public methods ──────────────────────────────────────────────────────

    async def nearby_search(
        self, *, lat: float, lon: float, radius_m: int,
        keyword: Optional[str] = None, place_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "location": f"{lat},{lon}",
            "radius": min(radius_m, 50000),
        }
        if keyword:
            params["keyword"] = keyword
        if place_type:
            params["type"] = place_type
        data = await self._get("/nearbysearch/json", params)
        return data.get("results", [])

    async def autocomplete(
        self, *, query: str, lat: Optional[float] = None,
        lon: Optional[float] = None, radius_m: int = 50000,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"input": query}
        if lat is not None and lon is not None:
            params["location"] = f"{lat},{lon}"
            params["radius"] = radius_m
        data = await self._get("/autocomplete/json", params)
        return data.get("predictions", [])

    async def details(self, *, place_id: str) -> Optional[dict[str, Any]]:
        params = {
            "place_id": place_id,
            "fields": "place_id,name,formatted_address,geometry/location,types",
        }
        data = await self._get("/details/json", params)
        return data.get("result")

    async def reverse_geocode(self, *, lat: float, lon: float) -> Optional[dict[str, Any]]:
        """Returns the most relevant Place at a coordinate, or None."""
        # Geocoding API lives at maps.googleapis.com/maps/api/geocode — not /place
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "latlng": f"{lat},{lon}",
            "key": self._settings.google_places_api_key,
        }
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            return None
        results = data.get("results") or []
        return results[0] if results else None
```

Wire it into the FastAPI lifespan in `backend/app/main.py`:

```python
# Inside lifespan(), after vision/nlp setup:
from app.services.google_places import GooglePlacesService
app.state.google_places = GooglePlacesService(settings)
# ... and in the shutdown half:
await app.state.google_places.aclose()
```

Add a dependency helper `backend/app/api/deps.py` (create if missing):

```python
from fastapi import Request
from app.services.google_places import GooglePlacesService


def get_google_places(request: Request) -> GooglePlacesService:
    return request.app.state.google_places
```

### 4. EXIF GPS extractor

Create `backend/app/services/exif.py`:

```python
"""Extract GPS coordinates from image EXIF, if present."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ExifTags

log = logging.getLogger(__name__)

_GPSINFO_TAG = next(k for k, v in ExifTags.TAGS.items() if v == "GPSInfo")


def _to_decimal(dms: tuple, ref: str) -> float:
    deg, minutes, seconds = (float(x) for x in dms)
    val = deg + minutes / 60.0 + seconds / 3600.0
    if ref in ("S", "W"):
        val = -val
    return val


def extract_gps(image_path: Path) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) from EXIF, or None if missing/invalid."""
    try:
        with Image.open(image_path) as img:
            exif = img._getexif() or {}
    except Exception as exc:
        log.warning("exif.read_failed path=%s err=%s", image_path, exc)
        return None

    gps = exif.get(_GPSINFO_TAG)
    if not gps:
        return None

    gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
    try:
        lat = _to_decimal(gps_tags["GPSLatitude"], gps_tags["GPSLatitudeRef"])
        lon = _to_decimal(gps_tags["GPSLongitude"], gps_tags["GPSLongitudeRef"])
    except (KeyError, ValueError, TypeError) as exc:
        log.info("exif.parse_failed path=%s err=%s", image_path, exc)
        return None

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return lat, lon
```

### 5. Pydantic schemas

Create `backend/app/schemas/place.py`:

```python
from __future__ import annotations
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PlaceSummary(BaseModel):
    """Map-marker-sized payload — sent in lists."""
    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID]                     # null for places we've never stored
    google_place_id: str
    name: str
    formatted_address: Optional[str]
    latitude: float
    longitude: float
    google_types: List[str] = Field(default_factory=list)
    aggregate_trust: float                  # 0.0 if no public contributions
    public_count: int                       # 0 if none
    contribution_count: int
    has_data: bool                          # has at least 1 PUBLIC contribution


class PlaceDetail(PlaceSummary):
    """Place page payload — includes most-recent contributions."""
    contributions: List["ContributionPin"]


class PlaceAutocomplete(BaseModel):
    google_place_id: str
    description: str                        # "Starbucks, MG Road, Bangalore"
    main_text: str
    secondary_text: Optional[str]


from app.schemas.contribution import ContributionPin  # noqa: E402  (forward ref)
PlaceDetail.model_rebuild()
```

### 6. Router `backend/app/api/routers/places.py`

```python
"""Place-centric discovery endpoints (Google Places + DB merge)."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_google_places
from app.core.config import Settings, get_settings
from app.db.models import Contribution, Place
from app.db.queries import find_nearby_places, upsert_place
from app.db.session import get_session
from app.schemas.place import PlaceAutocomplete, PlaceDetail, PlaceSummary
from app.schemas.contribution import ContributionPin
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

    google_results, db_places = await asyncio.gather(
        google.nearby_search(
            lat=latitude, lon=longitude, radius_m=radius_m,
            keyword=keyword, place_type=place_type,
        ),
        find_nearby_places(session, lat=latitude, lon=longitude, radius_m=radius_m, limit=200),
    )

    db_by_gid = {p.google_place_id: p for p in db_places}
    out: list[PlaceSummary] = []

    for g in google_results:
        gid = g.get("place_id")
        if not gid:
            continue
        db_row = db_by_gid.pop(gid, None)
        if db_row is not None:
            # Use DB row's trust + Google's name/types
            summary = _row_to_summary(db_row)
        else:
            summary = _google_to_summary(g)
        out.append(summary)

    # Tail-include DB places Google didn't surface
    for leftover in db_by_gid.values():
        out.append(_row_to_summary(leftover))

    response.headers["Cache-Control"] = "public, max-age=15"
    return out


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


@router.get("/{google_place_id}", response_model=PlaceDetail)
async def detail(
    google_place_id: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    google: GooglePlacesService = Depends(get_google_places),
) -> PlaceDetail:
    """Full place page: aggregate trust + recent contributions.

    If the place is not in our DB yet, we fetch its details from Google,
    *upsert* it (so subsequent calls hit the DB), and return zero contributions.
    """
    stmt = select(Place).where(Place.google_place_id == google_place_id)
    place = (await session.execute(stmt)).scalar_one_or_none()

    if place is None:
        details = await google.details(place_id=google_place_id)
        if not details:
            raise HTTPException(404, "Place not found")
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
        await session.commit()

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
        from pathlib import Path
        from app.api.routers.nearby import _compose_image_url
        pt = to_shape(c.location)
        return ContributionPin(
            id=c.id,
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
```

Register in `backend/app/main.py` `create_app()`:

```python
from app.api.routers.places import router as places_router
app.include_router(places_router)
```

### 7. Tests

Create `backend/tests/test_places.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_search_requires_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/places/search")
    assert r.status_code == 422  # missing required param


@pytest.mark.asyncio
async def test_nearby_validates_lat():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/places/nearby?latitude=999&longitude=0&radius_m=500")
    assert r.status_code == 422


# Skip live Google tests unless API key is present
import os
@pytest.mark.skipif(not os.getenv("GOOGLE_PLACES_API_KEY"), reason="no Places key")
@pytest.mark.asyncio
async def test_nearby_returns_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/api/v1/places/nearby?latitude=12.9716&longitude=77.5946&radius_m=500"
        )
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

Add `pytest-asyncio` config in `backend/pytest.ini` if not already enabled.

---

## Acceptance criteria

- [ ] `pip install -r backend/requirements.txt` succeeds (tenacity, cachetools added).
- [ ] `uvicorn app.main:app` starts without crashing when `GOOGLE_PLACES_API_KEY` is empty (the service initialises but raises on first call).
- [ ] `GET /api/v1/places/nearby?...` returns 503 with key empty, 200 with key set.
- [ ] `GET /api/v1/places/search?query=Starbucks` returns ≥1 prediction with key set.
- [ ] `GET /api/v1/places/{place_id}` upserts a row in `places` and returns `contributions: []` for an unknown place.
- [ ] `extract_gps` returns `(lat, lon)` for a known geo-tagged photo and `None` for one without GPS.
- [ ] Existing `/verify` and `/contributions/nearby` still pass.
- [ ] `python -m pytest -q` green.

## Smoke commands

```bash
# Start everything fresh
docker compose down -v && docker compose up -d && sleep 8
cd backend && alembic upgrade head
cd ..
GOOGLE_PLACES_API_KEY=YOUR_KEY ./run.sh -b   # backend only

# In a second terminal:
curl -s 'http://127.0.0.1:8000/api/v1/places/search?query=Starbucks' | jq '.[0]'
curl -s 'http://127.0.0.1:8000/api/v1/places/nearby?latitude=12.9716&longitude=77.5946&radius_m=500' | jq '.[0:2]'
PID=$(curl -s 'http://127.0.0.1:8000/api/v1/places/search?query=Starbucks+MG+Road+Bangalore' | jq -r '.[0].google_place_id')
curl -s "http://127.0.0.1:8000/api/v1/places/$PID" | jq '.name, .public_count'
```

## Pitfalls

- The Geocoding API is a separate billed product from Places API. Make sure
  the server-side key has both enabled in Google Cloud Console.
- `httpx.AsyncClient` keeps a connection pool — closing it in lifespan
  shutdown matters for clean tests.
- The TTL cache is *per process*. Behind a load balancer, each replica caches
  independently — fine for our scale but document it.
- EXIF GPS is often stripped by social-media platforms (Instagram, WhatsApp)
  before re-sharing. The fallback chain in phase 03 (EXIF → device GPS →
  user-typed address) is essential.
