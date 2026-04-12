"""
Health-check router for the NaviAble backend.

Endpoint: GET /health

Used by:
- The React frontend to detect whether the backend is reachable before
  displaying the submission form.
- Docker / Kubernetes liveness/readiness probes.
- Automated uptime monitors.

Response body:
    {
      "status": "healthy",
      "version": "1.0.0",
      "demo_mode": true,
      "services": {
        "yolo": "stub",       # or "loaded"
        "roberta": "stub"     # or "loaded"
      }
    }
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    summary="Backend Health Check",
    description=(
        "Returns the operational status of the NaviAble backend and its "
        "ML service singletons. Use this endpoint to verify the server is "
        "reachable and to determine whether real models are loaded."
    ),
)
async def health_check(request: Request) -> dict:
    """Return application health and ML service status.

    Parameters
    ----------
    request : Request
        Used to inspect ``app.state`` for loaded service instances.

    Returns
    -------
    dict
        Keys: ``status``, ``version``, ``demo_mode``, ``services``.
        ``services.yolo`` and ``services.roberta`` are either
        ``"loaded"`` (real weights in memory) or ``"stub"`` (no weights —
        demo / test mode).
    """
    from app.core.config import settings

    yolo_svc = getattr(request.app.state, "yolo_service", None)
    roberta_svc = getattr(request.app.state, "roberta_service", None)

    yolo_status = "loaded" if (yolo_svc and getattr(yolo_svc, "_model", None)) else "stub"
    clip_status = "loaded" if (yolo_svc and getattr(yolo_svc, "_clip_model", None)) else "stub"
    roberta_status = "loaded" if (roberta_svc and getattr(roberta_svc, "_pipeline", None)) else "stub"

    return {
        "status": "healthy",
        "version": "1.0.0",
        "demo_mode": settings.demo_mode,
        "services": {
            "yolo": yolo_status,
            "clip": clip_status,
            "roberta": roberta_status,
        },
    }
