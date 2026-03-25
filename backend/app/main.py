"""
NaviAble FastAPI Application Entry Point.

Startup / Shutdown Lifecycle
-----------------------------
FastAPI's ``@asynccontextmanager lifespan`` pattern is used (replacing the
deprecated ``@app.on_event`` hooks) to initialise both ML service singletons
during application startup and release resources on shutdown.

The two singletons are stored on ``app.state`` so that any router or
dependency can retrieve them via ``request.app.state``.

Usage (development server)
--------------------------
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.routers.verify import router as verify_router
from app.services.ml import RobertaNLPService, YoloVisionService

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

    yolo_service = YoloVisionService()
    roberta_service = RobertaNLPService()

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
        "RoBERTa validates the semantic genuineness of text reviews."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(verify_router)
