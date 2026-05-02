"""Validation tests for POST /api/v1/verify (no real DB or models needed)."""
import io
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vision import VisionResult


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _small_jpeg() -> bytes:
    """Return a minimal valid JPEG."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(100, 100, 100)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def app_with_stubs(tmp_path):
    """App with stub services and temp upload dir."""
    from app.main import create_app
    from app.services.vision import StubVisionService
    from app.services.nlp import StubNlpService
    from app.core.config import Settings, get_settings

    test_settings = Settings(
        database_url="postgresql+psycopg://x:x@localhost/test",
        upload_dir=str(tmp_path / "uploads"),
    )

    application = create_app()
    application.state.vision = StubVisionService()
    application.state.nlp = StubNlpService()

    # Override settings
    application.dependency_overrides[get_settings] = lambda: test_settings
    return application


@pytest.mark.anyio
async def test_missing_image_returns_422(app_with_stubs):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_stubs), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/verify",
            data={"review": "test ramp", "latitude": "12.97", "longitude": "77.59", "rating": "3"},
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_empty_review_returns_422(app_with_stubs, tmp_path):
    jpeg = _small_jpeg()
    async with AsyncClient(
        transport=ASGITransport(app=app_with_stubs), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/verify",
            files={"image": ("test.jpg", jpeg, "image/jpeg")},
            data={"review": "   ", "latitude": "12.97", "longitude": "77.59", "rating": "3"},
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_invalid_rating_returns_422(app_with_stubs):
    jpeg = _small_jpeg()
    async with AsyncClient(
        transport=ASGITransport(app=app_with_stubs), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/verify",
            files={"image": ("test.jpg", jpeg, "image/jpeg")},
            data={"review": "ramp test", "latitude": "12.97", "longitude": "77.59", "rating": "0"},
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_wrong_content_type_returns_415(app_with_stubs):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_stubs), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/verify",
            files={"image": ("test.txt", b"hello text", "text/plain")},
            data={"review": "ramp test", "latitude": "12.97", "longitude": "77.59", "rating": "3"},
        )
    assert resp.status_code == 415
