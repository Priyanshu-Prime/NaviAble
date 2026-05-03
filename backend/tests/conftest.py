"""Pytest configuration and fixtures."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def app_with_state():
    """Create app with proper lifespan initialization."""
    from app.main import create_app

    # Import this to ensure the app is created with lifespan
    from app.main import app as app_instance

    # The app should already have been created with lifespan
    return app_instance


@pytest_asyncio.fixture
async def async_client(app_with_state):
    """Create an async HTTP client."""
    transport = ASGITransport(app=app_with_state)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
