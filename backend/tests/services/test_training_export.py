"""Unit tests for training dataset export."""
import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

from app.services.training_export import export_training_dataset
from app.db.models import Contribution, TrainingExport


@pytest.fixture
def mock_contribution():
    """Create a mock contribution with PUBLIC visibility."""
    contrib = MagicMock(spec=Contribution)
    contrib.id = uuid4()
    contrib.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    contrib.visibility_status = "PUBLIC"
    contrib.image_path = "/tmp/test.jpg"
    contrib.text_note = "Accessible ramp at side entrance"
    contrib.trust_score = 0.85
    contrib.detected_features = {
        "ramp": [
            {"bbox": [10.0, 20.0, 100.0, 120.0], "confidence": 0.95}
        ]
    }
    return contrib


@pytest.mark.asyncio
async def test_export_creates_directory_structure(mock_contribution, tmp_path):
    """Export creates yolo/, roberta/, and manifest.json."""
    started_at = datetime.now(timezone.utc) - timedelta(days=5)
    ended_at = datetime.now(timezone.utc)

    # Create mock image file
    fake_image = tmp_path / "test.jpg"
    fake_image.write_bytes(b"fake image data")
    mock_contribution.image_path = str(fake_image)

    mock_session = MagicMock()
    export_dir = tmp_path / "exports"

    # Mock the async session.execute() call
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [mock_contribution]

    async def mock_execute(*args, **kwargs):
        return mock_execute_result

    mock_session.execute = mock_execute
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    result = await export_training_dataset(
        mock_session,
        out_dir=export_dir,
        started_at=started_at,
        ended_at=ended_at,
        notes="test export",
    )

    # Verify result
    assert result is not None
    assert result.contribution_count == 1
    assert result.yolo_image_count == 1
    assert result.roberta_row_count == 1


@pytest.mark.asyncio
async def test_export_writes_yolo_data_yaml(mock_contribution, tmp_path):
    """Export writes correct data.yaml with class mappings."""
    started_at = datetime.now(timezone.utc) - timedelta(days=5)

    fake_image = tmp_path / "test.jpg"
    fake_image.write_bytes(b"fake")
    mock_contribution.image_path = str(fake_image)

    mock_session = MagicMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [mock_contribution]

    async def mock_execute(*args, **kwargs):
        return mock_execute_result

    mock_session.execute = mock_execute
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    export_dir = tmp_path / "exports"
    result = await export_training_dataset(
        mock_session,
        out_dir=export_dir,
        started_at=started_at,
    )

    # Find and verify data.yaml
    yaml_files = list(export_dir.rglob("data.yaml"))
    assert len(yaml_files) == 1

    yaml_content = yaml_files[0].read_text()
    assert "0: ramp" in yaml_content
    assert "1: stairs" in yaml_content
    assert "2: steps" in yaml_content
    assert "3: handrail" in yaml_content


@pytest.mark.asyncio
async def test_export_writes_roberta_csv(mock_contribution, tmp_path):
    """Export writes RoBERTa train.csv with correct columns."""
    started_at = datetime.now(timezone.utc) - timedelta(days=5)

    fake_image = tmp_path / "test.jpg"
    fake_image.write_bytes(b"fake")
    mock_contribution.image_path = str(fake_image)

    mock_session = MagicMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [mock_contribution]

    async def mock_execute(*args, **kwargs):
        return mock_execute_result

    mock_session.execute = mock_execute
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    export_dir = tmp_path / "exports"
    result = await export_training_dataset(
        mock_session,
        out_dir=export_dir,
        started_at=started_at,
    )

    # Find and verify train.csv
    csv_files = list(export_dir.rglob("train.csv"))
    assert len(csv_files) == 1

    csv_content = csv_files[0].read_text()
    lines = csv_content.strip().split("\n")
    assert lines[0] == "text,label,trust_score,contribution_id"
    assert "Accessible ramp at side entrance" in lines[1]
    assert "1" in lines[1]  # label should be 1 for PUBLIC


@pytest.mark.asyncio
async def test_export_writes_manifest(mock_contribution, tmp_path):
    """Export writes manifest.json with metadata."""
    started_at = datetime.now(timezone.utc) - timedelta(days=5)
    ended_at = datetime.now(timezone.utc)

    fake_image = tmp_path / "test.jpg"
    fake_image.write_bytes(b"fake")
    mock_contribution.image_path = str(fake_image)

    mock_session = MagicMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [mock_contribution]

    async def mock_execute(*args, **kwargs):
        return mock_execute_result

    mock_session.execute = mock_execute
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    export_dir = tmp_path / "exports"
    result = await export_training_dataset(
        mock_session,
        out_dir=export_dir,
        started_at=started_at,
        ended_at=ended_at,
        notes="test export",
    )

    # Find and verify manifest.json
    manifest_files = list(export_dir.rglob("manifest.json"))
    assert len(manifest_files) == 1

    manifest_data = json.loads(manifest_files[0].read_text())
    assert "started_at" in manifest_data
    assert "ended_at" in manifest_data
    assert manifest_data["contribution_count"] == 1
    assert manifest_data["yolo_image_count"] == 1
    assert manifest_data["roberta_row_count"] == 1
    assert manifest_data["notes"] == "test export"


@pytest.mark.asyncio
async def test_export_handles_empty_detections(tmp_path):
    """Export handles contributions with no detected features."""
    contrib = MagicMock(spec=Contribution)
    contrib.id = uuid4()
    contrib.visibility_status = "PUBLIC"
    contrib.image_path = str(tmp_path / "test.jpg")
    contrib.text_note = "No features"
    contrib.trust_score = 0.6
    contrib.detected_features = {}

    fake_image = tmp_path / "test.jpg"
    fake_image.write_bytes(b"fake")

    mock_session = MagicMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [contrib]

    async def mock_execute(*args, **kwargs):
        return mock_execute_result

    mock_session.execute = mock_execute
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    started_at = datetime.now(timezone.utc) - timedelta(days=5)
    export_dir = tmp_path / "exports"

    result = await export_training_dataset(
        mock_session,
        out_dir=export_dir,
        started_at=started_at,
    )

    assert result is not None
    assert result.yolo_image_count == 1


@pytest.mark.asyncio
async def test_export_multiple_detections(tmp_path):
    """Export handles multiple bboxes per class."""
    contrib = MagicMock(spec=Contribution)
    contrib.id = uuid4()
    contrib.visibility_status = "PUBLIC"
    contrib.image_path = str(tmp_path / "multi.jpg")
    contrib.text_note = "Multiple features"
    contrib.trust_score = 0.9
    contrib.detected_features = {
        "ramp": [
            {"bbox": [10.0, 20.0, 100.0, 120.0], "confidence": 0.95},
            {"bbox": [150.0, 200.0, 250.0, 280.0], "confidence": 0.87},
        ],
        "stairs": [
            {"bbox": [300.0, 400.0, 400.0, 500.0], "confidence": 0.92},
        ]
    }

    fake_image = tmp_path / "multi.jpg"
    fake_image.write_bytes(b"fake")

    mock_session = MagicMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [contrib]

    async def mock_execute(*args, **kwargs):
        return mock_execute_result

    mock_session.execute = mock_execute
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    started_at = datetime.now(timezone.utc) - timedelta(days=5)
    export_dir = tmp_path / "exports"

    result = await export_training_dataset(
        mock_session,
        out_dir=export_dir,
        started_at=started_at,
    )

    # Find label file and verify it has 3 lines (2 ramps + 1 stairs)
    label_files = list(export_dir.rglob(f"{contrib.id}.txt"))
    assert len(label_files) == 1

    label_content = label_files[0].read_text()
    lines = label_content.strip().split("\n")
    assert len(lines) == 3
    assert lines[0].startswith("0 ")  # ramp (class 0)
