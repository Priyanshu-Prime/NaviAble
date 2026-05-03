"""Late-fusion trust score logic."""
from __future__ import annotations
from typing import Literal

from app.core.config import Settings


def compute_trust_score(vision: float, nlp: float, *, settings: Settings) -> float:
    """Weighted combination: 0.60 * vision + 0.40 * nlp."""
    if not (0.0 <= vision <= 1.0):
        raise ValueError(f"vision score out of range: {vision}")
    if not (0.0 <= nlp <= 1.0):
        raise ValueError(f"nlp score out of range: {nlp}")
    return round(settings.vision_weight * vision + settings.nlp_weight * nlp, 4)


def assign_status(trust_score: float) -> Literal["PUBLIC", "CAVEAT", "HIDDEN"]:
    """Map trust score to visibility bucket."""
    if trust_score >= 0.70:
        return "PUBLIC"
    if trust_score >= 0.20:
        return "CAVEAT"
    return "HIDDEN"
