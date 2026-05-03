"""Tests for the places API."""
import os

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_places_schemas_import():
    """Verify Place schemas can be imported."""
    from app.schemas.place import PlaceSummary, PlaceDetail, PlaceAutocomplete

    # Verify schemas are instantiable
    summary = PlaceSummary(
        id=None,
        google_place_id="test",
        name="Test Place",
        formatted_address="123 Test St",
        latitude=0.0,
        longitude=0.0,
        aggregate_trust=0.5,
        public_count=2,
        contribution_count=5,
        has_data=True,
    )
    assert summary.google_place_id == "test"
    assert summary.aggregate_trust == 0.5


@pytest.mark.anyio
async def test_google_places_service_creates():
    """Verify GooglePlacesService can be instantiated."""
    from app.core.config import Settings
    from app.services.google_places import GooglePlacesService

    settings = Settings(GOOGLE_PLACES_API_KEY="test-key")
    service = GooglePlacesService(settings)
    assert service is not None
    await service.aclose()


@pytest.mark.anyio
async def test_exif_service_imports():
    """Verify EXIF service can be imported."""
    from app.services.exif import extract_gps

    # Should not raise import error
    assert callable(extract_gps)


@pytest.mark.anyio
async def test_places_router_imports():
    """Verify places router can be imported."""
    from app.api.routers.places import router

    # Should not raise import error
    assert router is not None
    assert router.prefix == "/api/v1/places"


@pytest.mark.anyio
async def test_deps_imports():
    """Verify dependency helpers can be imported."""
    from app.api.deps import get_google_places

    assert callable(get_google_places)
