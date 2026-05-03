"""POST /api/v1/training/export — operator endpoint to cut a new dataset."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.services.training_export import export_training_dataset

router = APIRouter(prefix="/api/v1/training", tags=["training"])


class ExportRequest(BaseModel):
    started_at: datetime
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None
    out_dir: Optional[str] = None


class ExportResponse(BaseModel):
    id: UUID
    export_path: str
    contribution_count: int
    yolo_image_count: int
    roberta_row_count: int


@router.post("/export", response_model=ExportResponse)
async def export(
    body: ExportRequest,
    x_admin_token: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ExportResponse:
    expected = getattr(settings, "admin_token", None) or ""
    if not expected or x_admin_token != expected:
        raise HTTPException(401, "Admin token required")

    out_dir = Path(body.out_dir) if body.out_dir else Path("backend/training_exports")
    rec = await export_training_dataset(
        session,
        out_dir=out_dir,
        started_at=body.started_at,
        ended_at=body.ended_at,
        notes=body.notes,
    )
    return ExportResponse(
        id=rec.id,
        export_path=rec.export_path,
        contribution_count=rec.contribution_count,
        yolo_image_count=rec.yolo_image_count,
        roberta_row_count=rec.roberta_row_count,
    )
