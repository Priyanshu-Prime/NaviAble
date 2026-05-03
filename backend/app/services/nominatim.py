"""Free, open-source place search via Nominatim (OpenStreetMap).

Drop-in replacement for GooglePlacesService. Same method signatures, but backed by
Nominatim (https://nominatim.openstreetmap.org) instead of Google Places API.

No API key required. Slower and less comprehensive than Google, but "barely working"
for basic geocoding and place search.

Rate limit: max 1 request per second (policed by sleeping between calls).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx
from cachetools import TTLCache
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.services.google_places import GooglePlacesUnavailable

log = logging.getLogger(__name__)


class NominatimService:
    """Thin async wrapper around Nominatim REST API.

    Provides the same public interface as GooglePlacesService, but using
    OpenStreetMap data via Nominatim instead of Google Places API.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=settings.nominatim_timeout_s,
            base_url=settings.nominatim_base_url,
        )
        self._cache: TTLCache = TTLCache(
            maxsize=512, ttl=settings.nominatim_cache_ttl_s,
        )
        self._last_request_time = 0.0

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _rate_limit(self) -> None:
        elapsed = asyncio.get_event_loop().time() - self._last_request_time
        min_interval = 1.0  # Nominatim: max 1 req/sec
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.2, max=2.0),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        await self._rate_limit()
        params = {**params, "format": "json"}
        cache_key = (path, tuple(sorted(params.items())))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        headers = {"User-Agent": self._settings.nominatim_user_agent}
        try:
            resp = await self._client.get(path, params=params, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.error("nominatim.http_error path=%s err=%s", path, exc)
            raise GooglePlacesUnavailable(str(exc)) from exc

        data = resp.json()
        self._cache[cache_key] = data
        return data

    @staticmethod
    def _osm_to_place_id(osm_type: str, osm_id: int) -> str:
        """Convert OSM type+id to a stable place_id string.
        N=node, W=way, R=relation."""
        return f"{osm_type[0].upper()}{osm_id}"

    @staticmethod
    def _osmtype_to_types(row: dict) -> list[str]:
        """Map Nominatim category/type to a list for google_types."""
        category = row.get("category", "")
        return [category] if category else []

    async def reverse_geocode(self, *, lat: float, lon: float) -> Optional[dict[str, Any]]:
        """Reverse-geocode (lat,lon) → place name + OSM id.

        Returns a dict with place_id, formatted_address, types, and geometry.location.
        Nominatim returns a single result or None.
        """
        data = await self._get("/reverse", {"lat": lat, "lon": lon})
        if not data or "error" in data:
            return None

        osm_type = data.get("osm_type", "N")
        osm_id = data.get("osm_id", 0)
        return {
            "place_id": self._osm_to_place_id(osm_type, osm_id),
            "formatted_address": data.get("display_name", "Unnamed place"),
            "types": self._osmtype_to_types(data),
            "geometry": {
                "location": {
                    "lat": float(data.get("lat", lat)),
                    "lng": float(data.get("lon", lon)),
                }
            },
        }

    async def geocode_address(self, *, address: str) -> Optional[dict[str, Any]]:
        """Forward-geocode an address string.

        Returns a dict with place_id, formatted_address, types, and geometry.location.
        Nominatim returns an array; we take the first result.
        """
        data = await self._get("/search", {"q": address, "limit": 1})
        if not data or isinstance(data, dict) and "error" in data:
            return None

        results = data if isinstance(data, list) else data.get("results", [])
        if not results:
            return None

        r = results[0]
        osm_type = r.get("osm_type", "N")
        osm_id = r.get("osm_id", 0)
        return {
            "place_id": self._osm_to_place_id(osm_type, osm_id),
            "formatted_address": r.get("display_name", "Unnamed place"),
            "types": self._osmtype_to_types(r),
            "geometry": {
                "location": {
                    "lat": float(r.get("lat", 0.0)),
                    "lng": float(r.get("lon", 0.0)),
                }
            },
        }

    async def autocomplete(
        self, *, query: str, lat: Optional[float] = None,
        lon: Optional[float] = None, radius_m: int = 50000,
    ) -> list[dict[str, Any]]:
        """Search for places matching a query string.

        Nominatim doesn't have true autocomplete, but the search endpoint works.
        Returns a list of dicts with place_id, description, and structured_formatting.
        """
        params: dict[str, Any] = {"q": query, "limit": 10}
        if lat is not None and lon is not None:
            params["viewbox"] = f"{lon - 0.1},{lat + 0.1},{lon + 0.1},{lat - 0.1}"
            params["bounded"] = "1"

        data = await self._get("/search", params)
        if not data or isinstance(data, dict) and "error" in data:
            return []

        results = data if isinstance(data, list) else data.get("results", [])
        predictions = []
        for r in results:
            osm_type = r.get("osm_type", "N")
            osm_id = r.get("osm_id", 0)
            display_name = r.get("display_name", "")
            parts = display_name.split(",")
            main_text = parts[0].strip() if parts else ""
            secondary_text = (
                ", ".join(p.strip() for p in parts[1:]) if len(parts) > 1 else None
            )

            predictions.append({
                "place_id": self._osm_to_place_id(osm_type, osm_id),
                "description": display_name,
                "structured_formatting": {
                    "main_text": main_text,
                    "secondary_text": secondary_text,
                },
            })
        return predictions

    async def details(self, *, place_id: str) -> Optional[dict[str, Any]]:
        """Look up a place by its OSM id.

        place_id format: 'N12345' (node), 'W12345' (way), 'R12345' (relation).
        Returns a dict with place_id, name, formatted_address, geometry, and types.
        """
        if not place_id or len(place_id) < 2:
            return None

        try:
            data = await self._get("/lookup", {"osm_ids": place_id})
        except GooglePlacesUnavailable:
            return None

        if not data or isinstance(data, dict) and "error" in data:
            return None

        results = data if isinstance(data, list) else []
        if not results:
            return None

        r = results[0]
        osm_type = r.get("osm_type", "N")
        osm_id = r.get("osm_id", 0)
        display_name = r.get("display_name", "Unnamed place")
        name = display_name.split(",")[0].strip()

        return {
            "place_id": self._osm_to_place_id(osm_type, osm_id),
            "name": name,
            "formatted_address": display_name,
            "geometry": {
                "location": {
                    "lat": float(r.get("lat", 0.0)),
                    "lng": float(r.get("lon", 0.0)),
                }
            },
            "types": self._osmtype_to_types(r),
        }

    async def nearby_search(
        self, *, lat: float, lon: float, radius_m: int,
        keyword: Optional[str] = None, place_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return empty list — nearby search not supported in Nominatim.

        The /api/v1/places/nearby endpoint merges Google results with DB results.
        Without Google augmentation, it returns DB-only results, which is acceptable
        for "barely working" mode.
        """
        return []
