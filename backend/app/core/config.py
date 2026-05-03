"""Application settings.

Configuration is driven by environment variables (with optional ``.env`` file
support via pydantic-settings). Tests override settings by clearing the
``get_settings`` cache and constructing a new ``Settings`` instance with
explicit kwargs.

The ``vision_weight + nlp_weight`` invariant is enforced at construction
time so a misconfigured deployment fails to boot rather than silently
inflating Trust Scores.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+psycopg://naviable:naviable_dev@localhost:5434/naviable",
        description="Async SQLAlchemy URL for Postgres+PostGIS.",
    )

    # ── ML model paths ──────────────────────────────────────────────────────
    yolo_weights_path: str = Field(
        default="../YoloModel11/runs/stair_ramp_m4_v1/weights/best.pt",
        description="Path to fine-tuned YOLOv11 weights.",
    )
    roberta_checkpoint_dir: str = Field(
        default="../NaviAble_RoBERTa_Final",
        description="Path to RoBERTa HuggingFace checkpoint dir.",
    )

    # ── Google Places (server-side key) ─────────────────────────────────────
    google_places_api_key: str = Field(default="", alias="GOOGLE_PLACES_API_KEY")
    google_places_base_url: str = Field(
        default="https://maps.googleapis.com/maps/api/place",
    )
    google_places_timeout_s: float = Field(default=8.0)
    google_places_cache_ttl_s: int = Field(default=60)

    # ── Discovery / aggregation ─────────────────────────────────────────────
    nearby_default_radius_m: int = Field(default=800)
    nearby_max_radius_m: int = Field(default=10_000)
    trust_recency_half_life_days: int = Field(default=180)

    # ── Late fusion ─────────────────────────────────────────────────────────
    vision_threshold: float = Field(default=0.205, ge=0.0, le=1.0)
    vision_weight: float = Field(default=0.60, ge=0.0, le=1.0)
    nlp_weight: float = Field(default=0.40, ge=0.0, le=1.0)

    # ── Uploads ─────────────────────────────────────────────────────────────
    upload_dir: str = "backend/uploads"
    max_image_bytes: int = 10 * 1024 * 1024
    allowed_image_types: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
    )
    public_base_url: str = "http://localhost:8000"
    static_prefix: str = "/static/"

    # ── App ─────────────────────────────────────────────────────────────────
    demo_mode: bool = Field(default=False, alias="naviable_demo_mode")
    admin_token: str = Field(default="", alias="ADMIN_TOKEN")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        alias="naviable_cors_origins",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "Settings":
        total = self.vision_weight + self.nlp_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"vision_weight + nlp_weight must equal 1.0, got {total}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Tests can clear the cache via ``get_settings.cache_clear()``.
    """
    return Settings()


# Backwards-compatible module-level singleton for legacy imports.
settings = get_settings()
