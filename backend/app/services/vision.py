"""Vision service contract, result types, and YOLO implementation."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from pathlib import Path
from typing import Dict, List, Protocol

import imagehash
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from app.schemas.contribution import FeatureDetection

TARGET_CLASSES = ("ramp", "stairs", "steps", "handrail")
log = logging.getLogger(__name__)


class VisionResult(BaseModel):
    score: float
    detections: Dict[str, List[FeatureDetection]]
    image_phash: int


class VisionService(Protocol):
    async def score(self, image_path: Path) -> VisionResult: ...


class StubVisionService:
    async def score(self, image_path: Path) -> VisionResult:
        return VisionResult(score=0.5, detections={}, image_phash=0)


class VisionUnavailable(RuntimeError):
    """Vision model is unavailable — infrastructure failure."""


class YoloVisionService:
    def __init__(
        self,
        weights_path: Path,
        *,
        threshold: float = 0.205,
        cache_size: int = 256,
    ):
        from ultralytics import YOLO

        self._model = YOLO(str(weights_path))
        self._threshold = threshold
        self._cache: Dict[int, VisionResult] = {}
        self._cache_order: deque = deque(maxlen=cache_size)
        self._lock = asyncio.Lock()

    async def score(self, image_path: Path) -> VisionResult:
        try:
            phash = await asyncio.to_thread(self._compute_phash, image_path)
        except (UnidentifiedImageError, OSError) as exc:
            log.warning("vision.image_unreadable path=%s err=%s", image_path, exc)
            return VisionResult(score=0.0, detections={}, image_phash=0)

        cached = self._cache.get(phash)
        if cached is not None:
            return cached

        try:
            result = await asyncio.to_thread(self._infer, image_path, phash)
        except (RuntimeError, Exception) as exc:
            if "out of memory" in str(exc).lower() or isinstance(exc, MemoryError):
                log.error("vision.oom err=%s", exc)
                raise VisionUnavailable(str(exc)) from exc
            raise

        await self._remember(phash, result)
        return result

    def _compute_phash(self, image_path: Path) -> int:
        with Image.open(image_path) as img:
            return int(str(imagehash.phash(img)), 16)

    def _infer(self, image_path: Path, phash: int) -> VisionResult:
        from PIL import Image as PilImage

        with PilImage.open(image_path) as img:
            img_w, img_h = img.size

        results = self._model.predict(str(image_path), verbose=False, conf=self._threshold)

        detections: Dict[str, List[FeatureDetection]] = {}
        if results:
            for box in results[0].boxes:
                cls_name = self._model.names[int(box.cls[0])].lower()
                if cls_name not in TARGET_CLASSES:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                def _clamp(v: float) -> float:
                    return max(0.0, min(1.0, v))

                bbox = (
                    round(_clamp(x1 / img_w), 4),
                    round(_clamp(y1 / img_h), 4),
                    round(_clamp(x2 / img_w), 4),
                    round(_clamp(y2 / img_h), 4),
                )
                det = FeatureDetection(confidence=round(float(box.conf[0]), 4), bbox=bbox)
                detections.setdefault(cls_name, []).append(det)

        return VisionResult(
            score=self._aggregate_score(detections),
            detections=detections,
            image_phash=phash,
        )

    def _aggregate_score(self, detections: Dict[str, List[FeatureDetection]]) -> float:
        confidences = [d.confidence for boxes in detections.values() for d in boxes]
        return max(confidences, default=0.0)

    async def _remember(self, phash: int, result: VisionResult) -> None:
        async with self._lock:
            if phash in self._cache:
                return
            if len(self._cache_order) == self._cache_order.maxlen:
                evict = self._cache_order[0]
                self._cache.pop(evict, None)
            self._cache_order.append(phash)
            self._cache[phash] = result
