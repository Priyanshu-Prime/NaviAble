"""Export PUBLIC contributions into YOLO + RoBERTa-ready training datasets."""
from __future__ import annotations

import csv
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contribution, TrainingExport

log = logging.getLogger(__name__)

_CLASS_MAP = {"ramp": 0, "stairs": 1, "steps": 2, "handrail": 3}


async def export_training_dataset(
    session: AsyncSession,
    *,
    out_dir: Path,
    started_at: datetime,
    ended_at: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> TrainingExport:
    """Export PUBLIC contributions to YOLO and RoBERTa datasets."""
    ended_at = ended_at or datetime.now(timezone.utc)

    stmt = (
        select(Contribution)
        .where(Contribution.visibility_status == "PUBLIC")
        .where(Contribution.created_at >= started_at)
        .where(Contribution.created_at <= ended_at)
        .order_by(Contribution.created_at.asc())
    )
    rows = list((await session.execute(stmt)).scalars().all())

    stamp = ended_at.strftime("%Y%m%dT%H%M%S")
    dest = out_dir / stamp
    yolo_img = dest / "yolo" / "images"
    yolo_lab = dest / "yolo" / "labels"
    rob_dir = dest / "roberta"
    for d in (yolo_img, yolo_lab, rob_dir):
        d.mkdir(parents=True, exist_ok=True)

    yolo_count = 0
    roberta_rows = []

    for c in rows:
        # YOLO image + label
        src_img = Path(c.image_path)
        if src_img.exists():
            dst_img = yolo_img / f"{c.id}{src_img.suffix}"
            shutil.copy2(src_img, dst_img)
            label_path = yolo_lab / f"{c.id}.txt"
            with label_path.open("w") as f:
                for cls_name, dets in (c.detected_features or {}).items():
                    cls_idx = _CLASS_MAP.get(cls_name)
                    if cls_idx is None:
                        continue
                    for d in dets:
                        x1, y1, x2, y2 = d["bbox"]
                        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                        w, h = max(x2 - x1, 1e-6), max(y2 - y1, 1e-6)
                        f.write(f"{cls_idx} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
            yolo_count += 1
        # RoBERTa row (label = 1 since it's a verified PUBLIC review)
        roberta_rows.append({
            "text": c.text_note,
            "label": 1,
            "trust_score": c.trust_score,
            "contribution_id": str(c.id),
        })

    # data.yaml
    (dest / "yolo" / "data.yaml").write_text(
        "path: " + str(dest / "yolo") + "\n"
        "train: images\n"
        "val: images\n"
        "names:\n"
        "  0: ramp\n"
        "  1: stairs\n"
        "  2: steps\n"
        "  3: handrail\n"
    )

    csv_path = rob_dir / "train.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["text", "label", "trust_score", "contribution_id"]
        )
        writer.writeheader()
        writer.writerows(roberta_rows)

    manifest = {
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "contribution_count": len(rows),
        "yolo_image_count": yolo_count,
        "roberta_row_count": len(roberta_rows),
        "notes": notes or "",
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2))

    record = TrainingExport(
        export_path=str(dest),
        cutoff_started_at=started_at,
        cutoff_ended_at=ended_at,
        contribution_count=len(rows),
        yolo_image_count=yolo_count,
        roberta_row_count=len(roberta_rows),
        notes=notes,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    log.info(
        "training.export id=%s rows=%d dest=%s",
        record.id,
        len(rows),
        dest,
    )
    return record
