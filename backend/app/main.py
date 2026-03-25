"""
NaviAble FastAPI Application Entry Point.

Startup / Shutdown Lifecycle
-----------------------------
FastAPI's ``@asynccontextmanager lifespan`` pattern is used (replacing the
deprecated ``@app.on_event`` hooks) to initialise both ML service singletons
during application startup and release resources on shutdown.

The two singletons are stored on ``app.state`` so that any router or
dependency can retrieve them via ``request.app.state``.

CORS
----
Cross-Origin Resource Sharing is configured via the ``NAVIABLE_CORS_ORIGINS``
environment variable (see ``app.core.config``).  The React development server
runs on ``http://localhost:5173`` by default, which is included in the default
allow-list so the frontend works without any extra configuration.

Demo Mode
---------
Set ``NAVIABLE_DEMO_MODE=true`` to receive realistic synthetic inference
results even when model weights are not present.  Useful for development,
CI, and live demonstrations on hardware without a GPU.

Usage (development server)
--------------------------
    # From the backend/ directory:
    NAVIABLE_DEMO_MODE=true uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.health import router as health_router
from app.api.routers.verify import router as verify_router
from app.core.config import settings
from app.services.ml import RobertaNLPService, YoloVisionService

# Load .env file if python-dotenv is available.  This is intentionally
# best-effort: in production, environment variables should be injected by
# the deployment platform (Docker, systemd, CI) rather than a .env file.
# The ImportError is silenced so the app starts correctly without
# python-dotenv when real env vars are set by the host.
try:
    from dotenv import load_dotenv  # type: ignore[import-untyped]
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager.

    Executed *once* when the application starts and once when it shuts down.
    Loading both models here ensures:

    1. Memory is allocated exactly once per process (singleton pattern).
    2. The first real API request is not penalised by model-loading latency.
    3. Resource cleanup (if needed) occurs cleanly on SIGTERM / shutdown.

    Hardware note
    -------------
    YOLOv11 claims CUDA VRAM first.  RoBERTa is loaded on CPU by default
    (see ``RobertaNLPService.initialize`` for the ``ROBERTA_DEVICE`` override).
    This prevents CUDA OOM on the target GTX 1650 Ti (4 GB VRAM).
    """
    # ── Startup ────────────────────────────────────────────────────────
    logger.info("NaviAble backend starting up …")
    if settings.demo_mode:
        logger.info("DEMO MODE is ON — ML services will return synthetic results.")

    yolo_service = YoloVisionService(model_path=settings.yolo_model_path)
    roberta_service = RobertaNLPService(model_dir=settings.roberta_model_dir)

    yolo_service.initialize()
    roberta_service.initialize()

    # Attach singletons to app.state so routers can access them
    app.state.yolo_service = yolo_service
    app.state.roberta_service = roberta_service

    logger.info("ML services initialised. NaviAble backend is ready.")

    yield  # ← application runs here

    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("NaviAble backend shutting down. Releasing ML resources …")
    # Explicit deletion triggers Python's reference-counting GC which
    # in turn releases CUDA memory held by PyTorch tensors.
    del app.state.yolo_service
    del app.state.roberta_service
    logger.info("Shutdown complete.")


app = FastAPI(
    title="NaviAble Verification API",
    description=(
        "Dual-AI accessibility verification platform. "
        "YOLOv11 detects physical infrastructure from images; "
        "RoBERTa validates the semantic genuineness of text reviews. "
        "Set ``NAVIABLE_DEMO_MODE=true`` to run without model weights."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow the React dev server (port 5173) and any origins listed in settings.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(verify_router)
