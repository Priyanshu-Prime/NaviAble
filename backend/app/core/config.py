"""
Application Settings — NaviAble Backend.

All configuration is driven by environment variables so that the same
application image can run in demo mode, development, or production
without code changes.

Load order
----------
1. Defaults defined below.
2. A ``.env`` file in the working directory (loaded automatically when
   ``python-dotenv`` is installed).
3. Real environment variables (highest priority — override everything).

Environment Variables
---------------------
NAVIABLE_DEMO_MODE : bool (default: false)
    When ``true``, ML services return realistic synthetic results even
    when model weights are not present.  Use this for live demonstrations
    and development without GPU hardware.

NAVIABLE_CORS_ORIGINS : comma-separated string (default: see below)
    Allowed CORS origins.  Example:
        NAVIABLE_CORS_ORIGINS=http://localhost:5173,https://naviable.app

YOLO_MODEL_PATH : str (default: ./models/yolov11_naviable.pt)
    Filesystem path to the trained YOLOv11 ``.pt`` weights file.

ROBERTA_MODEL_DIR : str (default: ./NaviAble_RoBERTa_Final)
    Path to the saved HuggingFace RoBERTa model directory.

ROBERTA_DEVICE : str (default: cpu)
    Device to load RoBERTa on.  Use ``cuda`` or a device index (``0``)
    to load on GPU.  Defaults to CPU to avoid VRAM contention with YOLO
    on limited hardware (GTX 1650 Ti, 4 GB).
"""

from __future__ import annotations

import os

# ── Helper ──────────────────────────────────────────────────────────────────

def _bool_env(key: str, default: bool = False) -> bool:
    """Parse a boolean from an environment variable."""
    val = os.environ.get(key, str(default)).strip().lower()
    return val in ("1", "true", "yes", "on")


def _list_env(key: str, default: list[str]) -> list[str]:
    """Parse a comma-separated list from an environment variable."""
    raw = os.environ.get(key, "")
    if not raw.strip():
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


# ── Settings ─────────────────────────────────────────────────────────────────

class Settings:
    """Flat settings container populated from environment variables.

    Using a plain class (rather than Pydantic BaseSettings) keeps this
    module import-lightweight so it can be used in test environments
    that do not have the full dependency stack.
    """

    # Demo / development mode
    demo_mode: bool = _bool_env("NAVIABLE_DEMO_MODE", default=False)

    # CORS — allowed origins for the browser frontend
    cors_origins: list[str] = _list_env(
        "NAVIABLE_CORS_ORIGINS",
        default=[
            "http://localhost:5173",   # Vite dev server
            "http://localhost:3000",   # Create-React-App / alternate dev
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
    )

    # Model paths (forwarded to services)
    yolo_model_path: str = os.environ.get(
        "YOLO_MODEL_PATH", "./models/yolov11_naviable.pt"
    )
    roberta_model_dir: str = os.environ.get(
        "ROBERTA_MODEL_DIR", "./NaviAble_RoBERTa_Final"
    )


# Module-level singleton — import this everywhere
settings = Settings()
