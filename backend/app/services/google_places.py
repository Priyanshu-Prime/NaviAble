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

    async def geocode_address(self, *, address: str) -> Optional[dict[str, Any]]:
        """Forward-geocode an address string, return first result or None."""
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": self._settings.google_places_api_key,
        }
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            return None
        results = data.get("results") or []
        return results[0] if results else None
