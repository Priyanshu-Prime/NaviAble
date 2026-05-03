"""CLI: python -m app.cli.training_export --since 2025-01-01."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from app.db.session import SessionLocal
from app.services.training_export import export_training_dataset


def _parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _main(args: argparse.Namespace) -> None:
    async with SessionLocal() as session:
        rec = await export_training_dataset(
            session,
            out_dir=Path(args.out_dir),
            started_at=_parse_iso(args.since),
            ended_at=_parse_iso(args.until) if args.until else None,
            notes=args.notes,
        )
        print(
            f"export_id={rec.id} path={rec.export_path} "
            f"rows={rec.contribution_count}"
        )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--since", required=True, help="ISO8601 start")
    p.add_argument("--until", help="ISO8601 end (default: now)")
    p.add_argument("--out-dir", default="backend/training_exports")
    p.add_argument("--notes")
    asyncio.run(_main(p.parse_args()))


if __name__ == "__main__":
    main()
