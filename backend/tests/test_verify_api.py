"""
TDD Test Suite — POST /api/v1/verify endpoint.

These tests were authored BEFORE the implementation (strict TDD) and use
``unittest.mock.patch`` / ``AsyncMock`` to replace the real YOLOv11 and
RoBERTa services with predictable dummy data.  No ML weights are required
to run this suite.

Test Categories
---------------
1. Happy-path / golden-path assertion (full response schema validation).
2. Trust Score arithmetic (60 % vision + 40 % NLP).
3. Input validation — unsupported MIME type.
4. Input validation — oversized image.
5. Schema completeness — every required key is present in the response.
6. NLP-only confidence path (no visual features detected).
"""

from __future__ import annotations

import io
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_client() -> TestClient:
    """Create a ``TestClient`` with lifespan enabled so ``app.state`` is set."""
    return TestClient(app, raise_server_exceptions=True)


def _minimal_jpeg() -> bytes:
    """Return a 1×1 pixel JPEG as the smallest valid image payload."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


# Reusable dummy outputs from the two ML services
_DUMMY_VISION_RESULT: dict[str, Any] = {
    "objects_detected": 2,
    "features": [
        {"class": "ramp", "confidence": 0.62, "bbox": [10, 20, 150, 200]},
        {"class": "handrail", "confidence": 0.55, "bbox": [15, 25, 140, 190]},
    ],
}

_DUMMY_NLP_RESULT: dict[str, Any] = {
    "is_genuine": True,
    "confidence": 0.87,
    "label": "Genuine Physical Detail",
}


def _patch_ml_services(
    vision_result: dict[str, Any] = _DUMMY_VISION_RESULT,
    nlp_result: dict[str, Any] = _DUMMY_NLP_RESULT,
) -> tuple[Any, Any]:
    """Return two ``patch`` context managers that stub both ML singletons."""
    mock_yolo = MagicMock()
    mock_yolo.predict.return_value = vision_result

    mock_roberta = MagicMock()
    mock_roberta.classify.return_value = nlp_result

    return mock_yolo, mock_roberta


# ---------------------------------------------------------------------------
# Test: Happy Path — full golden-path assertion
# ---------------------------------------------------------------------------

class TestVerifyHappyPath:
    """Verify that a well-formed request returns HTTP 200 and a complete body."""

    def test_status_code_is_200(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "There is a ramp at the entrance.", "location_id": "00000000-0000-0000-0000-000000000001"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        assert resp.status_code == 200

    def test_response_status_field_is_success(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Wide accessible entrance.", "location_id": "00000000-0000-0000-0000-000000000002"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        body = resp.json()
        assert body["status"] == "success"

    def test_response_contains_data_key(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Ramp available.", "location_id": "00000000-0000-0000-0000-000000000003"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        assert "data" in resp.json()


# ---------------------------------------------------------------------------
# Test: Response Schema — every required key must be present
# ---------------------------------------------------------------------------

class TestVerifyResponseSchema:
    """Assert that the response strictly matches the API contract."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Smooth ramp at entrance.", "location_id": "00000000-0000-0000-0000-000000000004"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        self.body = resp.json()

    def test_data_has_nlp_analysis(self) -> None:
        assert "nlp_analysis" in self.body["data"]

    def test_data_has_vision_analysis(self) -> None:
        assert "vision_analysis" in self.body["data"]

    def test_data_has_naviable_trust_score(self) -> None:
        assert "naviable_trust_score" in self.body["data"]

    def test_nlp_analysis_has_is_genuine(self) -> None:
        assert "is_genuine" in self.body["data"]["nlp_analysis"]

    def test_nlp_analysis_has_confidence(self) -> None:
        assert "confidence" in self.body["data"]["nlp_analysis"]

    def test_nlp_analysis_has_label(self) -> None:
        assert "label" in self.body["data"]["nlp_analysis"]

    def test_vision_analysis_has_objects_detected(self) -> None:
        assert "objects_detected" in self.body["data"]["vision_analysis"]

    def test_vision_analysis_has_features(self) -> None:
        assert "features" in self.body["data"]["vision_analysis"]

    def test_vision_feature_has_class(self) -> None:
        assert self.body["data"]["vision_analysis"]["objects_detected"] == 2
        assert self.body["data"]["vision_analysis"]["features"][0]["class"] == "ramp"

    def test_vision_feature_bbox_is_four_ints(self) -> None:
        bbox = self.body["data"]["vision_analysis"]["features"][0]["bbox"]
        assert len(bbox) == 4
        assert all(isinstance(v, int) for v in bbox)


# ---------------------------------------------------------------------------
# Test: Trust Score Arithmetic
# ---------------------------------------------------------------------------

class TestTrustScoreCalculation:
    """Verify the 60/40 weighted trust score formula.

    Formula:  trust_score = 0.60 × mean_vision_conf + 0.40 × nlp_conf

    With the dummy data:
      vision_conf = mean(0.62, 0.55) = 0.585
      nlp_conf    = 0.87
      expected    = 0.60 × 0.585 + 0.40 × 0.87 = 0.351 + 0.348 = 0.699
    """

    _EXPECTED_TRUST_SCORE = round(0.60 * ((0.62 + 0.55) / 2) + 0.40 * 0.87, 4)

    def test_trust_score_matches_formula(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "There is a handrail.", "location_id": "00000000-0000-0000-0000-000000000005"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        trust = resp.json()["data"]["naviable_trust_score"]
        assert trust == pytest.approx(self._EXPECTED_TRUST_SCORE, abs=1e-4)

    def test_trust_score_is_between_0_and_1(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Accessible entrance.", "location_id": "00000000-0000-0000-0000-000000000006"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        trust = resp.json()["data"]["naviable_trust_score"]
        assert 0.0 <= trust <= 1.0


# ---------------------------------------------------------------------------
# Test: NLP-Only Path (no visual features)
# ---------------------------------------------------------------------------

class TestNoVisualFeatures:
    """When YOLO detects nothing, vision_conf should be 0 and score = 0.4 × nlp_conf."""

    def test_trust_score_when_no_features_detected(self) -> None:
        empty_vision: dict[str, Any] = {"objects_detected": 0, "features": []}
        mock_yolo, mock_roberta = _patch_ml_services(vision_result=empty_vision)
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Open area for wheelchair.", "location_id": "00000000-0000-0000-0000-000000000007"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        body = resp.json()
        expected = round(0.40 * _DUMMY_NLP_RESULT["confidence"], 4)
        assert body["data"]["naviable_trust_score"] == pytest.approx(expected, abs=1e-4)
        assert body["data"]["vision_analysis"]["objects_detected"] == 0


# ---------------------------------------------------------------------------
# Test: Input Validation — unsupported MIME type
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Bad requests must be rejected before reaching the ML pipeline."""

    def test_rejects_non_image_file(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Test review.", "location_id": "00000000-0000-0000-0000-000000000008"},
                files={"image": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
            )
        assert resp.status_code == 400

    def test_rejects_oversized_image(self) -> None:
        """Images larger than 10 MB must be rejected with HTTP 400."""
        oversized = b"\xff\xd8\xff" + b"x" * (10 * 1024 * 1024 + 1)
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Test.", "location_id": "00000000-0000-0000-0000-000000000009"},
                files={"image": ("big.jpg", oversized, "image/jpeg")},
            )
        assert resp.status_code == 400

    def test_accepts_png_images(self) -> None:
        """PNG images must be accepted alongside JPEG."""
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (2, 2), color=(0, 255, 0)).save(buf, format="PNG")
        png_bytes = buf.getvalue()

        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "PNG test.", "location_id": "00000000-0000-0000-0000-000000000010"},
                files={"image": ("photo.png", png_bytes, "image/png")},
            )
        assert resp.status_code == 200

    def test_missing_text_review_returns_422(self) -> None:
        """Omitting the required ``text_review`` field must yield HTTP 422."""
        with _make_client() as client:
            resp = client.post(
                "/api/v1/verify",
                data={"location_id": "00000000-0000-0000-0000-000000000011"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        assert resp.status_code == 422

    def test_missing_image_returns_422(self) -> None:
        """Omitting the required ``image`` file must yield HTTP 422."""
        with _make_client() as client:
            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Review text.", "location_id": "00000000-0000-0000-0000-000000000012"},
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test: NLP Analysis values are correctly propagated
# ---------------------------------------------------------------------------

class TestNLPAnalysisPropagation:
    """Verify that NLP result values flow through to the response unchanged."""

    def test_is_genuine_propagates(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "There is a ramp.", "location_id": "00000000-0000-0000-0000-000000000013"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        assert resp.json()["data"]["nlp_analysis"]["is_genuine"] is True

    def test_nlp_confidence_propagates(self) -> None:
        mock_yolo, mock_roberta = _patch_ml_services()
        with _make_client() as client:
            client.app.state.yolo_service = mock_yolo
            client.app.state.roberta_service = mock_roberta

            resp = client.post(
                "/api/v1/verify",
                data={"text_review": "Ramp at entrance.", "location_id": "00000000-0000-0000-0000-000000000014"},
                files={"image": ("test.jpg", _minimal_jpeg(), "image/jpeg")},
            )
        assert resp.json()["data"]["nlp_analysis"]["confidence"] == pytest.approx(0.87, abs=1e-4)
