"""Tests for the places API."""
import os

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
        r = await ac.get(
            "/api/v1/places/nearby?latitude=999&longitude=0&radius_m=500"
        )
    assert r.status_code == 422


# Skip live Google tests unless API key is present
@pytest.mark.skipif(
    not os.getenv("GOOGLE_PLACES_API_KEY"), reason="no Places key"
)
@pytest.mark.asyncio
async def test_nearby_returns_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/api/v1/places/nearby?latitude=12.9716&longitude=77.5946&radius_m=500"
        )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_nearby_default_params():
    """Test that /nearby works with minimal params."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/api/v1/places/nearby?latitude=12.9716&longitude=77.5946"
        )
    # Will fail with 503 if API key not set, but request should be valid
    assert r.status_code in (200, 503)
