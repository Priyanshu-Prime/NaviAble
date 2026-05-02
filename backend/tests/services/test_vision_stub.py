"""Tests for vision service stubs and aggregation."""
import asyncio
import pytest
from app.services.vision import StubVisionService, VisionResult
from app.schemas.contribution import FeatureDetection


def test_stub_returns_valid_result():
    svc = StubVisionService()
    result = asyncio.run(svc.score(None))
    assert isinstance(result, VisionResult)
    assert 0.0 <= result.score <= 1.0


def test_aggregate_score_empty():
    from app.services.vision import YoloVisionService
    # Test _aggregate_score as a standalone function behaviour
    # (test the logic without loading model weights)
    class FakeVision:
        _aggregate_score = YoloVisionService._aggregate_score

    fv = object.__new__(FakeVision)
    assert FakeVision._aggregate_score(fv, {}) == 0.0


def test_aggregate_score_max():
    from app.services.vision import YoloVisionService
    class FakeVision:
        _aggregate_score = YoloVisionService._aggregate_score

    fv = object.__new__(FakeVision)
    dets = {
        "ramp": [FeatureDetection(confidence=0.9, bbox=(0, 0, 0.5, 0.5))],
        "stairs": [FeatureDetection(confidence=0.6, bbox=(0, 0, 0.3, 0.3))],
    }
    assert FakeVision._aggregate_score(fv, dets) == 0.9
