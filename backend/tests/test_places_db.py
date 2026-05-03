"""DB-level smoke tests for Place model + helpers.

Skipped automatically when PostGIS isn't reachable.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.models import Contribution, Place
from app.db.queries import (
    find_nearby_places,
    recompute_place_aggregates,
    upsert_place,
)
from app.db.session import SessionLocal, ping


def _db_alive() -> bool:
    try:
        return asyncio.get_event_loop().run_until_complete(ping())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_alive(), reason="PostGIS not reachable",
)


@pytest.mark.asyncio
async def test_upsert_place_inserts_then_updates() -> None:
    async with SessionLocal() as s:
        # First insert
        gid = "test_gid_phase01_a"
        p1 = await upsert_place(
            s,
            google_place_id=gid,
            name="First Name",
            formatted_address="1 First St",
            lat=12.97, lon=77.59,
            google_types=["restaurant"],
        )
        await s.commit()
        assert p1.name == "First Name"

        # Re-insert with same gid → update
        p2 = await upsert_place(
            s,
            google_place_id=gid,
            name="Updated Name",
            formatted_address="2 Second St",
            lat=12.97, lon=77.59,
            google_types=["restaurant", "cafe"],
        )
        await s.commit()
        assert p2.id == p1.id, "upsert must keep the same row"
        assert p2.name == "Updated Name"
        assert p2.google_types == ["restaurant", "cafe"]

        # Cleanup
        await s.execute(
            select(Place).where(Place.google_place_id == gid)
        )


@pytest.mark.asyncio
async def test_find_nearby_places_within_radius() -> None:
    async with SessionLocal() as s:
        # Insert two places near Bangalore, one far away
        await upsert_place(
            s, google_place_id="near_bglr_1",
            name="Near 1", formatted_address=None,
            lat=12.9716, lon=77.5946, google_types=[],
        )
        await upsert_place(
            s, google_place_id="near_bglr_2",
            name="Near 2", formatted_address=None,
            lat=12.9750, lon=77.5950, google_types=[],
        )
        await upsert_place(
            s, google_place_id="far_delhi",
            name="Far", formatted_address=None,
            lat=28.6139, lon=77.2090, google_types=[],
        )
        await s.commit()

        nearby = await find_nearby_places(
            s, lat=12.9716, lon=77.5946, radius_m=5000,
        )
        ids = {p.google_place_id for p in nearby}
        assert "near_bglr_1" in ids
        assert "near_bglr_2" in ids
        assert "far_delhi" not in ids


@pytest.mark.asyncio
async def test_recompute_aggregates_uses_recency_weighted_mean() -> None:
    async with SessionLocal() as s:
        place = await upsert_place(
            s, google_place_id="aggregate_test_place",
            name="Aggr Test", formatted_address=None,
            lat=10.0, lon=10.0, google_types=[],
        )
        await s.commit()

        # Three PUBLIC contributions: trust 0.9, 0.8, 0.7
        # Aggregate should be near the mean (~0.8) since they're all "now"
        for trust in (0.9, 0.8, 0.7):
            row = Contribution(
                place_id=place.id,
                location="SRID=4326;POINT(10.0 10.0)",
                image_path="/tmp/x.jpg",
                text_note="ramp",
                rating=4,
                vision_score=trust,
                nlp_score=trust,
                trust_score=trust,
                visibility_status="PUBLIC",
                detected_features={},
            )
            s.add(row)
        # And one HIDDEN contribution that should NOT influence aggregate
        s.add(Contribution(
            place_id=place.id,
            location="SRID=4326;POINT(10.0 10.0)",
            image_path="/tmp/y.jpg",
            text_note="bad",
            rating=1,
            vision_score=0.1,
            nlp_score=0.1,
            trust_score=0.1,
            visibility_status="HIDDEN",
            detected_features={},
        ))
        await s.flush()
        await recompute_place_aggregates(s, place.id)
        await s.commit()
        await s.refresh(place)

        assert place.contribution_count == 4
        assert place.public_count == 3
        assert 0.78 <= place.aggregate_trust <= 0.82, (
            f"aggregate {place.aggregate_trust} should be ~0.8"
        )
