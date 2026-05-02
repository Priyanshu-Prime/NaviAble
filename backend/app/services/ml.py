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

Demo Mode
---------
Set the environment variable ``NAVIABLE_DEMO_MODE=true`` to make both
services return realistic *synthetic* results when model weights are not
present.  This allows the full API pipeline — including the React frontend
— to be demonstrated without a GPU or trained weights.

Demo mode behaviour:

- ``YoloVisionService``: returns 1–3 sample accessibility feature detections
  derived from the image byte-length so results vary between images.
- ``RobertaNLPService``: performs lightweight keyword analysis on the review
  text to produce plausible ``is_genuine`` and ``confidence`` values.

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

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
InferenceResult = dict[str, Any]

# ---------------------------------------------------------------------------
# Demo mode helpers
# ---------------------------------------------------------------------------

# Keywords indicating genuine physical accessibility descriptions.
# Used only in demo/stub mode — the real RoBERTa model performs semantic
# classification and does NOT rely on keyword matching.
_GENUINE_KEYWORDS: frozenset[str] = frozenset({
    "ramp", "handrail", "rail", "wheelchair", "elevator", "lift",
    "tactile", "braille", "grab bar", "curb cut", "accessible entrance",
    "flat entrance", "wide doorway", "doorway", "accessible parking",
    "accessible bathroom", "accessible toilet", "disabled parking",
    "slope", "incline", "gradient", "level access",
})

# Representative demo detections pool (mirrors the real YOLO class map)
_DEMO_DETECTION_POOL: list[dict[str, Any]] = [
    {"class": "ramp",              "confidence": 0.72, "bbox": [45,  120, 280, 380]},
    {"class": "handrail",          "confidence": 0.61, "bbox": [10,  50,  60,  350]},
    {"class": "flat_entrance",     "confidence": 0.55, "bbox": [100, 200, 400, 450]},
    {"class": "accessible_doorway","confidence": 0.63, "bbox": [80,  30,  320, 420]},
    {"class": "tactile_paving",    "confidence": 0.58, "bbox": [20,  400, 500, 480]},
]

_ACCESSIBILITY_PROMPTS: dict[str, list[str]] = {
    "ramp": [
        "a wheelchair ramp",
        "a sloped accessibility ramp",
        "a ramp for disabled access",
        "an outdoor wheelchair ramp",
    ],
    "stair": [
        "a staircase",
        "a staircase with multiple steps",
        "stairs in a building",
        "an indoor staircase",
    ],
    "step": [
        "a single step",
        "a small stair step",
        "one step in a walkway",
        "a curb step",
    ],
    "guard rail": [
        "a guard rail",
        "a handrail beside stairs",
        "a metal handrail",
        "a safety rail next to steps",
    ],
    "negative": [
        "flat ground",
        "no accessibility structure",
        "an empty sidewalk",
        "plain pavement",
    ],
}

_ACCESSIBILITY_ORDER = ["ramp", "stair", "step", "guard rail", "negative"]


def _resolve_clip_device() -> str:
    import torch  # type: ignore[import-untyped]

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _build_accessibility_inventory() -> tuple[list[str], dict[str, slice]]:
    prompts: list[str] = []
    class_slices: dict[str, slice] = {}
    start = 0
    for cls in _ACCESSIBILITY_ORDER:
        cls_prompts = _ACCESSIBILITY_PROMPTS[cls]
        prompts.extend(cls_prompts)
        class_slices[cls] = slice(start, start + len(cls_prompts))
        start += len(cls_prompts)
    return prompts, class_slices


def _best_accessibility_label(probs: Any, class_slices: dict[str, slice]) -> tuple[str, float]:
    class_scores: dict[str, float] = {}
    for cls in _ACCESSIBILITY_ORDER:
        idx_slice = class_slices[cls]
        class_scores[cls] = float(probs[idx_slice].mean().item())

    positive_scores = {k: v for k, v in class_scores.items() if k != "negative"}
    best_positive = max(positive_scores, key=positive_scores.get)
    best_positive_score = positive_scores[best_positive]
    negative_score = class_scores["negative"]

    if negative_score >= best_positive_score or best_positive_score < 0.15:
        return "negative", negative_score
    return best_positive, best_positive_score


def _make_clip_inputs(clip_processor: Any, prompts: list[str], images: list[Any], device: str) -> dict[str, Any]:
    inputs = clip_processor(text=prompts, images=images, return_tensors="pt", padding=True)
    return {k: v.to(device) for k, v in inputs.items()}


def _is_demo_mode() -> bool:
    """Return True when the NAVIABLE_DEMO_MODE environment variable is set."""
    return os.environ.get("NAVIABLE_DEMO_MODE", "false").strip().lower() in (
        "1", "true", "yes", "on"
    )


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
    - In demo mode (``NAVIABLE_DEMO_MODE=true``), return synthetic results
      that vary by image so the frontend can be demonstrated without weights.

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
        self._clip_model: Any = None
        self._clip_processor: Any = None
        self._clip_device: str = "cpu"

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

            logger.info("Loading YOLOv11 weights from %s ...", self.model_path)
            self._model = YOLO(self.model_path)
            logger.info("YOLOv11 loaded successfully.")
        except ImportError:
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

        try:
            import torch  # type: ignore[import-untyped]
            from transformers import CLIPModel, CLIPProcessor  # type: ignore[import-untyped]

            if not settings.enable_hybrid_clip:
                logger.info("Hybrid CLIP loading disabled by ENABLE_HYBRID_CLIP=false.")
                return

            self._clip_device = _resolve_clip_device()
            clip_model_name = os.environ.get("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
            logger.info("Loading CLIP model %s on %s ...", clip_model_name, self._clip_device)
            self._clip_processor = CLIPProcessor.from_pretrained(clip_model_name)
            self._clip_model = CLIPModel.from_pretrained(clip_model_name)
            self._clip_model.to(self._clip_device)
            self._clip_model.eval()
            logger.info("CLIP loaded successfully.")
        except ImportError:
            logger.warning("transformers CLIP components not installed. Hybrid inference disabled; falling back to YOLO-only vision.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("CLIP initialisation failed (%s). Falling back to YOLO-only vision.", exc)

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
            if self._clip_model is not None and self._clip_processor is not None:
                return self._clip_only_predict(image_bytes)
            if _is_demo_mode():
                return self._demo_predict(image_bytes)
            logger.warning("YOLOv11 model not loaded; returning empty result.")
            return {"objects_detected": 0, "features": []}

        if self._clip_model is not None and self._clip_processor is not None:
            return self._hybrid_predict(image_bytes)

        # Convert raw bytes -> numpy array via PIL to avoid disk I/O
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

    def _hybrid_predict(self, image_bytes: bytes) -> InferenceResult:
        """Run YOLO proposals and CLIP refinement for accessibility classes."""
        from PIL import Image  # type: ignore[import-untyped]
        import torch  # type: ignore[import-untyped]

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)

        results = self._model(img_array, conf=self.conf_threshold, iou=0.45)
        boxes = results[0].boxes

        candidate_boxes: list[tuple[list[float], float]] = []
        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                candidate_boxes.append((box.xyxy[0].tolist(), float(box.conf[0].item())))
        else:
            h, w = img_array.shape[:2]
            candidate_boxes.append(([0.0, 0.0, float(w), float(h)], self.conf_threshold))

        prompts, class_slices = _build_accessibility_inventory()

        crops: list[Image.Image] = []
        kept_boxes: list[tuple[list[float], float]] = []
        h, w = img_array.shape[:2]
        for box, yolo_conf in candidate_boxes:
            x1, y1, x2, y2 = [int(round(v)) for v in box]
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            if x2 <= x1 or y2 <= y1:
                continue
            crop = Image.fromarray(img_array[y1:y2, x1:x2])
            crops.append(crop)
            kept_boxes.append((box, yolo_conf))

        if not crops:
            return {"objects_detected": 0, "features": []}

        inputs = _make_clip_inputs(self._clip_processor, prompts, crops, self._clip_device)

        with torch.no_grad():
            outputs = self._clip_model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=-1)

        features: list[dict[str, Any]] = []
        for idx, (box, yolo_conf) in enumerate(kept_boxes):
            label, clip_score = _best_accessibility_label(probs[idx], class_slices)
            box, yolo_conf = kept_boxes[idx]
            fused_conf = float(0.35 * yolo_conf + 0.65 * clip_score)
            x1, y1, x2, y2 = [int(round(v)) for v in box]
            features.append(
                {
                    "class": label,
                    "confidence": round(fused_conf, 4),
                    "bbox": [x1, y1, x2, y2],
                }
            )

        return {"objects_detected": len(features), "features": features}

    def _clip_only_predict(self, image_bytes: bytes) -> InferenceResult:
        """Fallback when CLIP is present but YOLO weights are unavailable."""
        from PIL import Image  # type: ignore[import-untyped]
        import torch  # type: ignore[import-untyped]

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)
        h, w = img_array.shape[:2]

        prompts, class_slices = _build_accessibility_inventory()
        inputs = _make_clip_inputs(self._clip_processor, prompts, [image], self._clip_device)

        with torch.no_grad():
            outputs = self._clip_model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=-1)[0]

        label, clip_score = _best_accessibility_label(probs, class_slices)

        return {
            "objects_detected": 1,
            "features": [
                {
                    "class": label,
                    "confidence": round(float(clip_score), 4),
                    "bbox": [0, 0, w, h],
                }
            ],
        }

    def _demo_predict(self, image_bytes: bytes) -> InferenceResult:
        """Return synthetic detections for demo/development mode.

        Uses the image byte-length (mod 3) + 1 to select 1, 2, or 3
        detections from the pool, giving variety across different images
        without requiring real inference.

        Parameters
        ----------
        image_bytes : bytes
            The raw image — only its length is used as a variety seed.

        Returns
        -------
        InferenceResult
            Synthetic but realistic-looking detection results.
        """
        num_detections = (len(image_bytes) % 3) + 1
        features = _DEMO_DETECTION_POOL[:num_detections]
        logger.info("DEMO MODE: returning %d synthetic YOLO detections.", num_detections)
        return {"objects_detected": len(features), "features": features}


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

yolo_service = YoloVisionService()
roberta_service = RobertaNLPService()
