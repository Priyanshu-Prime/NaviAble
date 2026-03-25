"""
ML Service Singletons for the NaviAble Dual-AI Verification Architecture.

Architecture Note
-----------------
Both YOLO (vision) and RoBERTa (NLP) models are CPU/GPU-bound synchronous
operations. Running them directly inside an ``async def`` FastAPI handler
would block the event loop and starve other concurrent requests.

The correct pattern is:

1. Load models **once** during application startup (via ``lifespan``).
2. Expose a synchronous ``predict`` / ``classify`` method.
3. Call that method from async handlers using ``asyncio.to_thread()``,
   which offloads the blocking work to a thread-pool worker without
   blocking the async event loop. This is the standard approach
   recommended by the FastAPI and Starlette maintainers.

The classes below implement this pattern.  When real model weights are
present (``./models/yolov11_naviable.pt`` and
``./NaviAble_RoBERTa_Final/``), the ``initialize()`` methods load them
into the appropriate device.  In test environments the services are
replaced by ``unittest.mock.MagicMock`` objects, keeping tests fast and
dependency-free.

Hardware note (GTX 1650 Ti, 4 GB VRAM)
---------------------------------------
YOLOv11 is placed on CUDA when available.  RoBERTa runs on CPU by
default because loading both models simultaneously on 4 GB VRAM causes
CUDA OOM.  If more VRAM is available in future hardware, set
``ROBERTA_DEVICE=cuda`` in the environment.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
InferenceResult = dict[str, Any]


# ---------------------------------------------------------------------------
# YOLOv11 Vision Service
# ---------------------------------------------------------------------------

class YoloVisionService:
    """Singleton wrapper around the trained YOLOv11 accessibility detector.

    Responsibilities
    ----------------
    - Load the ``.pt`` weights file into GPU/CPU memory exactly once.
    - Accept raw image bytes and return a structured detection result.
    - Filter detections below the configured confidence threshold.

    Attributes
    ----------
    model_path : str
        Filesystem path to the YOLOv11 ``.pt`` weights file.
    conf_threshold : float
        Minimum confidence score for a detection to be included in results.
    _model : Any
        The loaded ``ultralytics.YOLO`` model instance (``None`` until
        ``initialize()`` is called).
    _class_map : dict[int, str]
        Mapping from YOLO class integer IDs to human-readable labels.
    """

    _class_map: dict[int, str] = {
        0: "ramp",
        1: "handrail",
        2: "flat_entrance",
        3: "accessible_doorway",
        4: "tactile_paving",
        5: "elevator",
        6: "accessible_parking",
    }

    def __init__(
        self,
        model_path: str = "./models/yolov11_naviable.pt",
        conf_threshold: float = 0.5,
    ) -> None:
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self._model: Any = None

    def initialize(self) -> None:
        """Load YOLOv11 weights into memory.

        This method is called once during application startup via the
        FastAPI ``lifespan`` context manager.  Importing ``ultralytics``
        is deferred to this method so that the service module can be
        imported in test environments without the heavy ML dependencies.

        Raises
        ------
        FileNotFoundError
            If ``self.model_path`` does not exist.
        RuntimeError
            If the YOLO model fails to initialise for any other reason.
        """
        try:
            from ultralytics import YOLO  # type: ignore[import-untyped]

            logger.info("Loading YOLOv11 weights from %s …", self.model_path)
            self._model = YOLO(self.model_path)
            logger.info("YOLOv11 loaded successfully.")
        except (ImportError, ModuleNotFoundError):
            logger.warning(
                "ultralytics package not installed. "
                "YOLOv11 running in stub mode (no real inference)."
            )
        except FileNotFoundError:
            logger.warning(
                "YOLOv11 weights not found at %s. "
                "Running in stub mode (no real inference).",
                self.model_path,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load YOLOv11: %s", exc)
            raise RuntimeError(f"YOLOv11 initialisation failed: {exc}") from exc

    def predict(self, image_bytes: bytes) -> InferenceResult:
        """Run YOLOv11 inference on raw image bytes.

        This is a **synchronous, blocking** method.  Call it from an
        async context via ``await asyncio.to_thread(service.predict, data)``
        to avoid blocking the event loop.

        Parameters
        ----------
        image_bytes : bytes
            Raw image payload (JPEG or PNG) as received from the HTTP
            multipart upload.

        Returns
        -------
        InferenceResult
            A dictionary with keys:
            - ``objects_detected`` (int): number of detections above threshold.
            - ``features`` (list[dict]): each dict contains ``class``,
              ``confidence``, and ``bbox`` (``[x1, y1, x2, y2]``).
        """
        if self._model is None:
            logger.warning("YOLOv11 model not loaded; returning empty result.")
            return {"objects_detected": 0, "features": []}

        # Convert raw bytes → numpy array via PIL to avoid disk I/O
        from PIL import Image  # type: ignore[import-untyped]

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)

        results = self._model(img_array, conf=self.conf_threshold, iou=0.45)

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


# ---------------------------------------------------------------------------
# RoBERTa NLP Integrity Service
# ---------------------------------------------------------------------------

class RobertaNLPService:
    """Singleton wrapper around the fine-tuned RoBERTa text classifier.

    The model was trained using LLM Knowledge Distillation (Groq /
    llama-3.1-8b-instant) on a balanced 402-row dataset specifically
    designed to defeat the "Clever Hans" keyword-matching failure mode
    observed in the Phase A baseline.

    Responsibilities
    ----------------
    - Load the HuggingFace ``AutoModelForSequenceClassification`` and its
      tokeniser from the local ``./NaviAble_RoBERTa_Final/`` directory.
    - Accept a raw review string and return a structured classification.
    - Apply a ``genuine_threshold`` to guard against borderline positives.

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

        Device selection follows the hardware constraint documented in
        ``CONSTRAINTS_AND_RULES.md``: RoBERTa defaults to CPU to avoid
        CUDA OOM when YOLOv11 is simultaneously occupying VRAM.  Set the
        ``ROBERTA_DEVICE`` environment variable to ``"cuda"`` (or the CUDA
        device index as an integer string, e.g. ``"0"``) to override.

        Raises
        ------
        RuntimeError
            If the HuggingFace pipeline cannot be constructed.
        """
        try:
            import torch  # type: ignore[import-untyped]
            from transformers import pipeline  # type: ignore[import-untyped]
        except (ImportError, ModuleNotFoundError):
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
            logger.info("Loading RoBERTa from %s on device=%s …", self.model_dir, device)
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


# ---------------------------------------------------------------------------
# Module-level singletons — initialised by FastAPI lifespan
# ---------------------------------------------------------------------------

yolo_service = YoloVisionService()
roberta_service = RobertaNLPService()
