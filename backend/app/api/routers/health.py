"""Health check endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.session import engine as _engine

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict:
    """Liveness + DB reachability check."""
    from sqlalchemy import text
    db_ok = True
    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {"status": "ok", "db": "ok" if db_ok else "fail"}


# Keep /health for backward compatibility
@router.get("/health")
async def health() -> dict:
    return await healthz()
