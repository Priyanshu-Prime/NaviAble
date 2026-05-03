"""Unit tests for location resolver chain."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.location_resolver import resolve_place
from app.services.google_places import GooglePlacesService, GooglePlacesUnavailable
from app.db.models import Place


@pytest.fixture
def image_path(tmp_path):
    """Create a temporary image file."""
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fake image data")
    return img


@pytest.mark.asyncio
async def test_resolve_by_coordinates(image_path):
    """Resolve using explicit (latitude, longitude)."""
    mock_session = MagicMock()
    mock_google = MagicMock()

    with patch('app.services.location_resolver._resolve_from_coords', new_callable=AsyncMock) as mock_resolve:
        mock_place = MagicMock(spec=Place)
        mock_resolve.return_value = (mock_place, 40.7128, -74.0060)

        place, lat, lon = await resolve_place(
            mock_session,
            mock_google,
            google_place_id=None,
            latitude=40.7128,
            longitude=-74.0060,
            address=None,
            image_path=image_path,
        )

    assert place == mock_place
    assert lat == 40.7128
    assert lon == -74.0060


@pytest.mark.asyncio
async def test_resolve_by_exif(image_path):
    """Resolve using EXIF GPS data from image."""
    mock_session = MagicMock()
    mock_google = MagicMock()

    with patch('app.services.location_resolver.extract_gps') as mock_extract:
        mock_extract.return_value = (51.5074, -0.1278)  # London

        with patch('app.services.location_resolver._resolve_from_coords', new_callable=AsyncMock) as mock_resolve:
            mock_place = MagicMock(spec=Place)
            mock_resolve.return_value = (mock_place, 51.5074, -0.1278)

            place, lat, lon = await resolve_place(
                mock_session,
                mock_google,
                google_place_id=None,
                latitude=None,
                longitude=None,
                address=None,
                image_path=image_path,
            )

    assert place == mock_place
    assert lat == 51.5074
    assert lon == -0.1278


@pytest.mark.asyncio
async def test_resolve_by_address(image_path):
    """Resolve using address string."""
    mock_session = MagicMock()
    mock_google = AsyncMock()

    with patch('app.services.location_resolver.extract_gps') as mock_extract:
        mock_extract.return_value = None

        mock_google.geocode_address = AsyncMock(return_value={
            "geometry": {
                "location": {
                    "lat": 48.8566,
                    "lng": 2.3522,
                }
            },
            "formatted_address": "Paris, France",
        })

        with patch('app.services.location_resolver._resolve_from_coords', new_callable=AsyncMock) as mock_resolve:
            mock_place = MagicMock(spec=Place)
            mock_resolve.return_value = (mock_place, 48.8566, 2.3522)

            place, lat, lon = await resolve_place(
                mock_session,
                mock_google,
                google_place_id=None,
                latitude=None,
                longitude=None,
                address="Paris, France",
                image_path=image_path,
            )

    assert place == mock_place
    assert lat == 48.8566
    assert lon == 2.3522


@pytest.mark.asyncio
async def test_resolve_all_signals_missing(image_path):
    """Raise 422 when all location signals fail."""
    mock_session = MagicMock()
    mock_google = MagicMock()

    with patch('app.services.location_resolver.extract_gps') as mock_extract:
        mock_extract.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await resolve_place(
                mock_session,
                mock_google,
                google_place_id=None,
                latitude=None,
                longitude=None,
                address=None,
                image_path=image_path,
            )

    assert exc_info.value.status_code == 422
    assert "Could not determine location" in exc_info.value.detail
