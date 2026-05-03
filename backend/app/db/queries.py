"""Spatial queries and place mutations.

`find_nearby` is the legacy spatial helper used by ``GET /contributions/nearby``.
`find_nearby_places` powers the place-centric map view.
`upsert_place` and `recompute_place_aggregates` are called from the verify
endpoint so place rows stay consistent with their contribution children.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contribution, Place

if TYPE_CHECKING:
    pass


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


async def find_nearby_places(
    session: AsyncSession,
    *,
    lat: float,
    lon: float,
    radius_m: float,
    limit: int = 200,
    min_trust: float = 0.0,
) -> list[Place]:
    """Return places within radius_m, sorted by distance, filtered by min trust.

    ``min_trust=0.0`` (default) returns every place we know about, even those
    with no PUBLIC contributions yet — the UI tints them grey ("no data").
    """
    distance_expr = text(
        "ST_Distance(location::geography, "
        "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)"
    )
    within_expr = text(
        "ST_DWithin(location::geography, "
        "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)"
    )

    stmt = (
        select(Place)
        .where(within_expr)
        .where(Place.aggregate_trust >= min_trust)
        .order_by(distance_expr.asc())
        .limit(limit)
        .params(lat=lat, lon=lon, radius_m=radius_m)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def upsert_place(
    session: AsyncSession,
    *,
    google_place_id: str,
    name: str,
    formatted_address: str | None,
    lat: float,
    lon: float,
    google_types: list[str],
) -> Place:
    """Insert-or-update a place by ``google_place_id``. Returns the live row.

    On conflict, the name/address/types are refreshed (places do get
    renamed) but the location is intentionally left frozen — moving a
    place would break the aggregate-by-coordinate semantics.
    """
    stmt = (
        pg_insert(Place)
        .values(
            google_place_id=google_place_id,
            name=name,
            formatted_address=formatted_address,
            location=text("ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)").bindparams(
                lon=lon, lat=lat,
            ),
            google_types=google_types,
        )
        .on_conflict_do_update(
            index_elements=["google_place_id"],
            set_=dict(
                name=name,
                formatted_address=formatted_address,
                google_types=google_types,
                updated_at=text("now()"),
            ),
        )
        .returning(Place)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def recompute_place_aggregates(
    session: AsyncSession,
    place_id: UUID,
    *,
    half_life_days: int = 180,
) -> None:
    """Recompute denormalised counters on the place row.

    The aggregate trust is a recency-weighted mean over PUBLIC contributions:
    a contribution submitted today has full weight; one ``half_life_days``
    old has weight 0.5; one ``2 * half_life_days`` old has weight 0.25.
    Hidden rows do not affect the aggregate but still increment the total
    contribution_count so we can show "23 contributions, 17 verified".
    """
    await session.execute(
        text(
            """
            UPDATE places p
            SET contribution_count = stats.total,
                public_count       = stats.public_count,
                aggregate_trust    = COALESCE(stats.weighted_trust, 0.0),
                last_contribution_at = stats.last_at,
                updated_at = now()
            FROM (
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE visibility_status = 'PUBLIC') AS public_count,
                    MAX(created_at) AS last_at,
                    CASE
                        WHEN COUNT(*) FILTER (WHERE visibility_status = 'PUBLIC') = 0
                            THEN 0.0
                        ELSE
                          SUM(trust_score *
                              EXP(-LN(2) *
                                  EXTRACT(EPOCH FROM (now() - created_at))
                                  / (:hl * 86400)))
                              FILTER (WHERE visibility_status = 'PUBLIC')
                          /
                          NULLIF(SUM(EXP(-LN(2) *
                                  EXTRACT(EPOCH FROM (now() - created_at))
                                  / (:hl * 86400)))
                              FILTER (WHERE visibility_status = 'PUBLIC'), 0)
                    END AS weighted_trust
                FROM contributions
                WHERE place_id = :pid
            ) stats
            WHERE p.id = :pid
            """
        ),
        {"pid": str(place_id), "hl": half_life_days},
    )
