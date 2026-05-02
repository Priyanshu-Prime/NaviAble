"""
ML Service Singletons for NaviAble.

Architecture Note
-----------------
Both YOLOv10 (vision) and RoBERTa (NLP) models are CPU/GPU-bound synchronous
operations. Running them directly inside an ``async def`` FastAPI handler
would block the event loop and starve other concurrent requests.

The correct pattern is:

1. Load models **once** during application startup (via ``lifespan``).
2. Expose a synchronous ``predict`` / ``classify`` method.
3. Call that method from async handlers using ``asyncio.to_thread()``,
   which offloads the blocking work to a thread-pool worker without
   blocking the async event loop.

Demo Mode
---------
Set ``NAVIABLE_DEMO_MODE=true`` to receive realistic synthetic results
when model weights are not present. This allows the full API pipeline
to be demonstrated without a GPU or trained weights.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Any

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
InferenceResult = dict[str, Any]

def _is_demo_mode() -> bool:
    """Return True when the NAVIABLE_DEMO_MODE environment variable is set."""
    return os.environ.get("NAVIABLE_DEMO_MODE", "false").strip().lower() in (
        "1", "true", "yes", "on"
    )




# ---------------------------------------------------------------------------
# YOLOv10 Vision Service (Optimized for Ramp & Stair Detection)
# ---------------------------------------------------------------------------

class YoloV10Service:
    """Specialized YOLOv10 model for ramp and stair accessibility detection.

    This service is optimized for detecting two critical accessibility features:
    - Ramp: wheelchair-accessible inclined ramps
    - Stair: staircases or steps (may indicate accessibility barriers)

    Trained on 11,173 images with excellent performance:
    - mAP@50: 0.837 (83.7% accuracy)
    - mAP@50-95: 0.611 (multi-scale detection)
    - Precision: 0.874 (low false positives)
    - Recall: 0.877 (high object detection)

    The model is optimized for M4 Pro and runs on CPU/MPS/CUDA.
    """

    _class_map: dict[int, str] = {
        0: "ramp",
        1: "stair",
    }

    def __init__(
        self,
        model_path: str | None = None,
        conf_threshold: float = 0.5,
    ) -> None:
        """Initialize the YOLOv10 service.

        Parameters
        ----------
        model_path : str, optional
            Path to the trained YOLOv10 weights file (best.pt).
            If None, uses YOLO_V10_MODEL environment variable or default.
        conf_threshold : float
            Minimum confidence score (0-1) for detections to be included.
        """
        from pathlib import Path

        if model_path is None:
            # Try environment variable first, then default
            model_path = os.environ.get(
                "YOLO_V10_MODEL",
                "../YoloModel11/runs/stair_ramp_m4_v1/weights/best.pt"
            )

        # Convert to absolute path
        model_path_obj = Path(model_path)
        if not model_path_obj.is_absolute():
            model_path = str((Path.cwd() / model_path_obj).resolve())

        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self._model: Any = None

    def initialize(self) -> None:
        """Load YOLOv10 weights into memory at startup.

        This is called once during application startup via the FastAPI
        lifespan context manager. The model is loaded on the best available
        device (MPS for M4, CUDA if available, else CPU).
        """
        try:
            from ultralytics import YOLO
            import torch
            from pathlib import Path

            # Resolve the model path
            model_path = Path(self.model_path)
            if not model_path.is_absolute():
                # If relative, resolve from current working directory
                model_path = Path.cwd() / model_path

            logger.info("Loading YOLOv10 weights from %s ...", model_path)

            # Check if file exists before loading
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found at {model_path}")

            logger.info("Model file exists: %s (size: %.1f MB)", model_path, model_path.stat().st_size / 1e6)

            self._model = YOLO(str(model_path))

            # Detect best device
            if torch.backends.mps.is_available():
                device = 'mps'
                logger.info("YOLOv10 will run on Apple Silicon (MPS)")
            elif torch.cuda.is_available():
                device = 0  # First CUDA device
                logger.info("YOLOv10 will run on NVIDIA GPU (CUDA)")
            else:
                device = 'cpu'
                logger.info("YOLOv10 will run on CPU")

            self._device = device
            logger.info("✅ YOLOv10 loaded successfully (mAP50: 0.837, mAP50-95: 0.611)")

        except ImportError as exc:
            logger.error(
                "ultralytics package not installed. "
                "YOLOv10 cannot run. Error: %s",
                exc
            )
        except FileNotFoundError as exc:
            logger.error(
                "YOLOv10 weights file not found. Error: %s",
                exc
            )
        except Exception as exc:
            logger.error("Failed to load YOLOv10: %s", exc)
            import traceback
            logger.error("Full traceback: %s", traceback.format_exc())

    def predict(self, image_bytes: bytes) -> InferenceResult:
        """Run YOLOv10 inference on raw image bytes.

        This is a synchronous, blocking method. Call from async context via:
            await asyncio.to_thread(service.predict, image_bytes)

        Parameters
        ----------
        image_bytes : bytes
            Raw JPEG or PNG image data.

        Returns
        -------
        InferenceResult
            Dictionary with:
            - objects_detected (int): number of detections above threshold
            - features (list[dict]): each has 'class', 'confidence', 'bbox'
        """
        if self._model is None:
            if _is_demo_mode():
                return self._demo_predict(image_bytes)
            logger.warning("YOLOv10 model not loaded; returning empty result.")
            return {"objects_detected": 0, "features": []}

        # Convert bytes to image array
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)

        # Run inference
        results = self._model(img_array, conf=self.conf_threshold, iou=0.45)

        # Extract detections
        features: list[dict[str, Any]] = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            features.append(
                {
                    "class": self._class_map.get(cls_id, f"class_{cls_id}"),
                    "confidence": round(conf, 4),
                    "bbox": [x1, y1, x2, y2],
                }
            )

        return {"objects_detected": len(features), "features": features}

    def _demo_predict(self, image_bytes: bytes) -> InferenceResult:
        """Return synthetic detections in demo mode."""
        demo_pool = [
            {"class": "ramp", "confidence": 0.87, "bbox": [50, 150, 400, 450]},
            {"class": "stair", "confidence": 0.79, "bbox": [100, 200, 350, 500]},
        ]
        num_detections = (len(image_bytes) % 2) + 1
        features = demo_pool[:num_detections]
        logger.info("DEMO MODE: returning %d synthetic YOLOv10 detections.", num_detections)
        return {"objects_detected": len(features), "features": features}


# ---------------------------------------------------------------------------
# RoBERTa NLP Integrity Service
# ---------------------------------------------------------------------------

class RobertaNLPService:
    """Singleton wrapper around the fine-tuned RoBERTa text classifier.

    The model was trained using LLM Knowledge Distillation on a balanced
    402-row dataset designed to defeat keyword-memorisation failure modes.

    Responsibilities
    ----------------
    - Load the HuggingFace ``AutoModelForSequenceClassification`` and its
      tokeniser from the local ``./NaviAble_RoBERTa_Final/`` directory.
    - Accept a raw review string and return a structured classification.
    - Apply a ``genuine_threshold`` to guard against borderline positives.
    - In demo mode, perform lightweight keyword analysis instead of real
      inference so the frontend can be demonstrated without model weights.

    Attributes
    ----------
    model_dir : str
        Path to the saved HuggingFace model directory.
    genuine_threshold : float
        Minimum Class-1 probability required to label a review as genuine.
        Defaults to 0.75 to minimise false positives.
    _pipeline : Any
        The HuggingFace ``pipeline`` object (``None`` until ``initialize()``).
    """

    # Label mapping matching the training data convention
    _label_map: dict[str, str] = {
        "LABEL_0": "Generic / Non-specific praise",
        "LABEL_1": "Genuine Physical Detail",
    }

    def __init__(
        self,
        model_dir: str = "./NaviAble_RoBERTa_Final",
        genuine_threshold: float = 0.75,
    ) -> None:
        self.model_dir = model_dir
        self.genuine_threshold = genuine_threshold
        self._pipeline: Any = None

    def initialize(self) -> None:
        """Load RoBERTa weights and tokeniser into memory.

        Device selection follows the hardware constraint: RoBERTa defaults
        to CPU to avoid CUDA OOM when YOLOv11 is simultaneously occupying
        VRAM.  Set the ``ROBERTA_DEVICE`` environment variable to ``"cuda"``
        (or the CUDA device index as an integer string, e.g. ``"0"``) to
        override.

        Raises
        ------
        RuntimeError
            If the HuggingFace pipeline cannot be constructed.
        """
        try:
            import torch  # type: ignore[import-untyped]
            from transformers import pipeline  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                "torch / transformers packages not installed. "
                "RoBERTa running in stub mode (no real inference)."
            )
            return

        env_device = os.environ.get("ROBERTA_DEVICE", "cpu")
        try:
            device = int(env_device)  # numeric CUDA index
        except ValueError:
            device = 0 if (env_device.lower() == "cuda" and torch.cuda.is_available()) else -1

        try:
            logger.info("Loading RoBERTa from %s on device=%s ...", self.model_dir, device)
            self._pipeline = pipeline(
                "text-classification",
                model=self.model_dir,
                tokenizer=self.model_dir,
                device=device,
                truncation=True,
                max_length=512,
            )
            logger.info("RoBERTa loaded successfully.")
        except OSError:
            logger.warning(
                "RoBERTa model directory not found at %s. "
                "Running in stub mode (no real inference).",
                self.model_dir,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load RoBERTa: %s", exc)
            if _is_demo_mode():
                logger.warning(
                    "DEMO MODE: proceeding without RoBERTa due to model load failure."
                )
                return
            raise RuntimeError(f"RoBERTa initialisation failed: {exc}") from exc

    def classify(self, text: str) -> InferenceResult:
        """Classify a review text for accessibility content genuineness.

        This is a **synchronous, blocking** method.  Call it from an
        async context via ``await asyncio.to_thread(service.classify, text)``
        to avoid blocking the event loop.

        Pre-processing
        --------------
        - Strip excess whitespace and normalise newlines.
        - Truncation to 512 tokens is handled by the HuggingFace pipeline.

        Parameters
        ----------
        text : str
            The raw review text submitted by the user.

        Returns
        -------
        InferenceResult
            A dictionary with keys:

            - ``is_genuine`` (bool): True if Class-1 probability exceeds
              ``genuine_threshold``.
            - ``confidence`` (float): Model probability for the predicted class.
            - ``label`` (str): Human-readable label string.
        """
        if self._pipeline is None:
            if _is_demo_mode():
                return self._demo_classify(text)
            logger.warning("RoBERTa pipeline not loaded; returning stub result.")
            return {
                "is_genuine": False,
                "confidence": 0.0,
                "label": self._label_map["LABEL_0"],
            }

        # Minimal sanitisation: collapse whitespace
        cleaned = " ".join(text.split())

        raw = self._pipeline(cleaned)[0]
        hf_label: str = raw["label"]       # e.g. "LABEL_1"
        score: float = float(raw["score"])  # probability of the predicted label

        is_genuine = hf_label == "LABEL_1" and score >= self.genuine_threshold

        # When the model predicts LABEL_0, ``score`` is the P(class_0) probability.
        # Normalise so that ``confidence`` always reflects P(class_1).
        confidence = score if hf_label == "LABEL_1" else 1.0 - score

        return {
            "is_genuine": is_genuine,
            "confidence": round(confidence, 4),
            "label": self._label_map.get(hf_label, hf_label),
        }

    def _demo_classify(self, text: str) -> InferenceResult:
        """Perform lightweight keyword-based classification for demo mode.

        This is NOT a substitute for the trained RoBERTa model.  It is a
        simple heuristic that counts genuine-accessibility keyword matches in
        the review text to produce plausible-looking output for live demos.

        Scoring heuristic
        -----------------
        - 0 keyword matches: ``is_genuine=False``, confidence approx 0.12-0.25
        - 1 keyword match:   ``is_genuine=True``,  confidence approx 0.76
        - 2+ keyword matches: ``is_genuine=True``, confidence approx 0.80-0.96
          (capped at 0.96 to avoid artificially perfect scores)

        Parameters
        ----------
        text : str
            The raw review text.

        Returns
        -------
        InferenceResult
            Plausible synthetic NLP classification result.
        """
        text_lower = text.lower()
        matches = [kw for kw in _GENUINE_KEYWORDS if kw in text_lower]
        num = len(matches)

        if num == 0:
            # No accessibility keywords -> likely generic praise
            confidence = round(0.10 + (len(text) % 15) / 100, 4)
            return {
                "is_genuine": False,
                "confidence": confidence,
                "label": self._label_map["LABEL_0"],
            }

        # Scale confidence with number of distinct keyword matches
        base = 0.76 + min(num - 1, 5) * 0.04
        confidence = round(min(base, 0.96), 4)
        logger.info(
            "DEMO MODE: NLP classified as genuine (keywords=%s, conf=%.2f).",
            matches[:3], confidence,
        )
        return {
            "is_genuine": True,
            "confidence": confidence,
            "label": self._label_map["LABEL_1"],
        }


# ---------------------------------------------------------------------------
# Module-level singletons — initialised by FastAPI lifespan
# ---------------------------------------------------------------------------

roberta_service = RobertaNLPService()
