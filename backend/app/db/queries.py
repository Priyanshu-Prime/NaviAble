"""Spatial queries.

`find_nearby` is the only public function. The discovery endpoint imports
it; nothing else should reach into the geometry column directly.
"""

from __future__ import annotations

from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contribution


async def find_nearby(
    session: AsyncSession,
    *,
    lat: float,
    lon: float,
    radius_m: float,
    include_caveat: bool = True,
    limit: int = 200,
) -> list[Contribution]:
    """Return public (and optionally caveat) contributions within radius_m.

    Uses ``ST_DWithin`` on the geography cast so the radius is metres,
    independent of latitude. ``HIDDEN`` rows are never returned.
    """
    statuses: list[str] = ["PUBLIC"]
    if include_caveat:
        statuses.append("CAVEAT")

    distance_expr = text(
        "ST_Distance(location::geography, "
        "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)"
    )
    within_expr = text(
        "ST_DWithin(location::geography, "
        "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)"
    )

    stmt = (
        select(Contribution)
        .where(within_expr)
        .where(Contribution.visibility_status.in_(statuses))
        .order_by(distance_expr.asc())
        .limit(limit)
        .params(lat=lat, lon=lon, radius_m=radius_m)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
