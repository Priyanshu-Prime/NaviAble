"""Integration tests for training export API endpoint."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException

from app.api.routers.training import export, ExportRequest, ExportResponse
from app.core.config import Settings
from app.db.models import TrainingExport


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_settings_with_token():
    """Settings with admin token."""
    settings = MagicMock(spec=Settings)
    settings.admin_token = "test-token-secret"
    return settings


@pytest.fixture
def mock_settings_no_token():
    """Settings without admin token."""
    settings = MagicMock(spec=Settings)
    settings.admin_token = ""
    return settings


@pytest.mark.asyncio
async def test_training_export_requires_admin_token(mock_session, mock_settings_no_token):
    """Endpoint rejects requests without valid admin token."""
    body = ExportRequest(
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
        ended_at=datetime.now(timezone.utc),
    )

    with pytest.raises(HTTPException) as exc_info:
        await export(
            body=body,
            x_admin_token="wrong-token",
            session=mock_session,
            settings=mock_settings_no_token,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_training_export_with_valid_token(mock_session, mock_settings_with_token):
    """Endpoint accepts requests with valid admin token."""
    body = ExportRequest(
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
        ended_at=datetime.now(timezone.utc),
    )

    mock_training_export = MagicMock(spec=TrainingExport)
    mock_training_export.id = uuid4()
    mock_training_export.export_path = "/exports/20250503T120000"
    mock_training_export.contribution_count = 10
    mock_training_export.yolo_image_count = 10
    mock_training_export.roberta_row_count = 10

    with patch('app.api.routers.training.export_training_dataset', new_callable=AsyncMock) as mock_export:
        mock_export.return_value = mock_training_export

        response = await export(
            body=body,
            x_admin_token="test-token-secret",
            session=mock_session,
            settings=mock_settings_with_token,
        )

    assert response is not None
    assert response.id == mock_training_export.id
    assert response.export_path == "/exports/20250503T120000"
    assert response.contribution_count == 10


@pytest.mark.asyncio
async def test_training_export_missing_token_header(mock_session, mock_settings_with_token):
    """Endpoint rejects requests without token header."""
    body = ExportRequest(
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
    )

    with pytest.raises(HTTPException) as exc_info:
        await export(
            body=body,
            x_admin_token=None,  # No token provided
            session=mock_session,
            settings=mock_settings_with_token,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_training_export_uses_default_out_dir(mock_session, mock_settings_with_token):
    """Uses 'backend/training_exports' as default output directory."""
    body = ExportRequest(
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
        out_dir=None,  # Not provided
    )

    mock_training_export = MagicMock(spec=TrainingExport)
    mock_training_export.id = uuid4()
    mock_training_export.export_path = "/exports/test"
    mock_training_export.contribution_count = 0
    mock_training_export.yolo_image_count = 0
    mock_training_export.roberta_row_count = 0

    with patch('app.api.routers.training.export_training_dataset', new_callable=AsyncMock) as mock_export:
        mock_export.return_value = mock_training_export

        response = await export(
            body=body,
            x_admin_token="test-token-secret",
            session=mock_session,
            settings=mock_settings_with_token,
        )

    # Verify the call was made with default directory
    call_args = mock_export.call_args
    assert "backend/training_exports" in str(call_args)


@pytest.mark.asyncio
async def test_training_export_custom_out_dir(mock_session, mock_settings_with_token):
    """Respects custom output directory."""
    body = ExportRequest(
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
        out_dir="/custom/export/path",
    )

    mock_training_export = MagicMock(spec=TrainingExport)
    mock_training_export.id = uuid4()
    mock_training_export.export_path = "/custom/export/path/20250503T120000"
    mock_training_export.contribution_count = 0
    mock_training_export.yolo_image_count = 0
    mock_training_export.roberta_row_count = 0

    with patch('app.api.routers.training.export_training_dataset', new_callable=AsyncMock) as mock_export:
        mock_export.return_value = mock_training_export

        response = await export(
            body=body,
            x_admin_token="test-token-secret",
            session=mock_session,
            settings=mock_settings_with_token,
        )

    # Verify the call used custom directory
    call_args = mock_export.call_args
    assert "/custom/export/path" in str(call_args)


@pytest.mark.asyncio
async def test_training_export_with_notes(mock_session, mock_settings_with_token):
    """Passes notes to export service."""
    body = ExportRequest(
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
        notes="Q1 2025 dataset cut",
    )

    mock_training_export = MagicMock(spec=TrainingExport)
    mock_training_export.id = uuid4()
    mock_training_export.export_path = "/exports/test"
    mock_training_export.contribution_count = 0
    mock_training_export.yolo_image_count = 0
    mock_training_export.roberta_row_count = 0

    with patch('app.api.routers.training.export_training_dataset', new_callable=AsyncMock) as mock_export:
        mock_export.return_value = mock_training_export

        response = await export(
            body=body,
            x_admin_token="test-token-secret",
            session=mock_session,
            settings=mock_settings_with_token,
        )

    # Verify notes were passed
    call_args = mock_export.call_args
    assert "Q1 2025 dataset cut" in str(call_args)


@pytest.mark.asyncio
async def test_training_export_response_schema(mock_session, mock_settings_with_token):
    """Response contains all required fields."""
    body = ExportRequest(
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
    )

    export_id = uuid4()
    mock_training_export = MagicMock(spec=TrainingExport)
    mock_training_export.id = export_id
    mock_training_export.export_path = "/exports/20250503T120000"
    mock_training_export.contribution_count = 25
    mock_training_export.yolo_image_count = 25
    mock_training_export.roberta_row_count = 25

    with patch('app.api.routers.training.export_training_dataset', new_callable=AsyncMock) as mock_export:
        mock_export.return_value = mock_training_export

        response = await export(
            body=body,
            x_admin_token="test-token-secret",
            session=mock_session,
            settings=mock_settings_with_token,
        )

    # Verify response is correct type
    assert isinstance(response, ExportResponse)
    assert response.id == export_id
    assert response.export_path == "/exports/20250503T120000"
    assert response.contribution_count == 25
    assert response.yolo_image_count == 25
    assert response.roberta_row_count == 25
