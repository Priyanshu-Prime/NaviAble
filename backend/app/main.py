"""NaviAble FastAPI application."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware, get_request_id


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    log = logging.getLogger(__name__)

    log.info("naviable.startup")

    # Load vision service
    from app.services.vision import YoloVisionService, StubVisionService
    weights = Path(settings.yolo_weights_path)
    if weights.exists():
        vision = YoloVisionService(weights, threshold=settings.vision_threshold)
        # Warmup
        warmup = Path(__file__).parent / "static" / "warmup.jpg"
        if warmup.exists():
            await vision.score(warmup)
            log.info("vision.warmup.complete")
    else:
        log.warning("vision.weights_missing path=%s — using stub", weights)
        vision = StubVisionService()

    # Load NLP service
    from app.services.nlp import RobertaNlpService, StubNlpService
    roberta_dir = Path(settings.roberta_checkpoint_dir)
    if roberta_dir.exists():
        nlp = RobertaNlpService(roberta_dir)
        await nlp.score("warmup accessibility ramp review")
        log.info("nlp.warmup.complete")
    else:
        log.warning("nlp.checkpoint_missing path=%s — using stub", roberta_dir)
        nlp = StubNlpService()

    app.state.vision = vision
    app.state.nlp = nlp
    log.info("naviable.ready")

    yield

    log.info("naviable.shutdown")
    del app.state.vision
    del app.state.nlp


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="NaviAble API",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Middleware (order matters: add outermost last)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    # Global error handler — never leak tracebacks
    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger(__name__).exception("unhandled_error rid=%s", get_request_id())
        return JSONResponse(
            status_code=500,
            content={"detail": "internal error", "request_id": get_request_id()},
        )

    # Routers
    from app.api.routers.health import router as health_router
    from app.api.routers.verify import router as verify_router
    from app.api.routers.nearby import router as nearby_router
    app.include_router(health_router)
    app.include_router(verify_router)
    app.include_router(nearby_router)

    # Static files (uploads served in dev)
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(upload_dir)), name="static")

    return app


app = create_app()
