# Phase 01 — Database & Migrations (places + place-keyed contributions + training exports)

**Status:** not started
**Depends on:** existing `0001_initial.py` migration (creates `contributions` table)
**Affects:** `backend/app/db/models.py`, `backend/app/db/queries.py`, `backend/alembic/versions/`

## Goal

The current schema has one table — `contributions` — keyed only by raw
`(latitude, longitude)`. To support a place-centric UI ("show me trust per
place, not per pin") we add:

1. A `places` table keyed by Google `place_id` with **denormalised aggregates**
   (running mean trust, contribution count, last submission time).
2. A `place_id` foreign key on `contributions` so multiple contributions
   (different users, different days) roll up to the same place.
3. A `training_exports` table that records every retraining dataset cut, so
   we can ask "what data was used to train v3?" and never re-export rows we
   already used.

We **do not** drop or rebuild `contributions` — there's no production data
yet, but the schema-additive approach keeps the path safe regardless.

---

## Deliverables

### 1. Update `backend/app/db/models.py`

Add the two new models and one column. Keep the existing `Contribution` body
unchanged except for the new `place_id` column and relationship.

```python
"""SQLAlchemy ORM models for NaviAble."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Place(Base):
    """A real-world location, keyed by Google Places `place_id`."""
    __tablename__ = "places"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    google_place_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    formatted_address: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False,
    )
    google_types: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))

    # Denormalised aggregates — recomputed inside the verify transaction.
    contribution_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    public_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    aggregate_trust: Mapped[float] = mapped_column(nullable=False, server_default=text("0.0"))
    last_contribution_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    contributions: Mapped[list["Contribution"]] = relationship(back_populates="place")

    __table_args__ = (
        CheckConstraint(
            "aggregate_trust BETWEEN 0 AND 1", name="places_trust_range",
        ),
        Index("places_location_gix", "location", postgresql_using="gist"),
    )


class Contribution(Base):
    __tablename__ = "contributions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # NEW: nullable so legacy rows survive; new rows always set this.
    place_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False,
    )
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_phash: Mapped[Optional[int]] = mapped_column(nullable=True)
    text_note: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    vision_score: Mapped[float] = mapped_column(nullable=False)
    nlp_score: Mapped[float] = mapped_column(nullable=False)
    trust_score: Mapped[float] = mapped_column(nullable=False)
    visibility_status: Mapped[str] = mapped_column(String(16), nullable=False)
    detected_features: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    place: Mapped[Optional["Place"]] = relationship(back_populates="contributions")

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="contributions_rating_range"),
        CheckConstraint("vision_score BETWEEN 0 AND 1", name="contributions_vision_range"),
        CheckConstraint("nlp_score BETWEEN 0 AND 1", name="contributions_nlp_range"),
        CheckConstraint("trust_score BETWEEN 0 AND 1", name="contributions_trust_range"),
        CheckConstraint(
            "visibility_status IN ('PUBLIC','CAVEAT','HIDDEN')",
            name="contributions_visibility_enum",
        ),
        Index("contributions_location_gix", "location", postgresql_using="gist"),
        Index("contributions_status_idx", "visibility_status"),
        Index("contributions_place_idx", "place_id"),
    )


class TrainingExport(Base):
    """One row per retraining dataset cut. Bookkeeping for the model loop."""
    __tablename__ = "training_exports"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    export_path: Mapped[str] = mapped_column(Text, nullable=False)
    cutoff_started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    cutoff_ended_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    contribution_count: Mapped[int] = mapped_column(Integer, nullable=False)
    yolo_image_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    roberta_row_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
```

### 2. Generate the alembic migration

From the `backend/` directory:

```bash
cd backend
source ../.venv/bin/activate   # or use .venv/bin/activate as set up in run.sh
alembic revision --autogenerate -m "add_places_and_training_exports"
```

Review the generated file in `backend/alembic/versions/<hash>_add_places_and_training_exports.py`.
**Adjust if needed** — autogen sometimes misses GIST indexes. The final
`upgrade()` body should include:

```python
def upgrade() -> None:
    op.create_table(
        "places",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("google_place_id", sa.String(255), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("formatted_address", sa.Text()),
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("google_types", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("contribution_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("public_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aggregate_trust", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_contribution_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("aggregate_trust BETWEEN 0 AND 1", name="places_trust_range"),
        sa.UniqueConstraint("google_place_id", name="places_google_place_id_key"),
    )
    op.create_index("places_location_gix", "places", ["location"], postgresql_using="gist")
    op.create_index("ix_places_google_place_id", "places", ["google_place_id"])

    op.add_column("contributions", sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_contributions_place_id", "contributions", "places",
        ["place_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("contributions_place_idx", "contributions", ["place_id"])

    op.create_table(
        "training_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("export_path", sa.Text(), nullable=False),
        sa.Column("cutoff_started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("cutoff_ended_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("contribution_count", sa.Integer(), nullable=False),
        sa.Column("yolo_image_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("roberta_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
```

Make sure the imports include:
```python
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql
```

### 3. Add a place-aware spatial query helper

Edit `backend/app/db/queries.py` to add `find_nearby_places`:

```python
async def find_nearby_places(
    session: AsyncSession,
    *,
    lat: float,
    lon: float,
    radius_m: float,
    limit: int = 50,
    min_trust: float = 0.0,
) -> list["Place"]:
    """Return places within radius_m, sorted by distance, filtered by min trust.

    `min_trust=0.0` (default) returns every place we know about, even those
    with no PUBLIC contributions yet — the UI tints them grey ("no data").
    """
    from app.db.models import Place

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
```

### 4. Add an `upsert_place` helper

Same file. PostgreSQL `ON CONFLICT (google_place_id) DO UPDATE` keeps the
operation atomic.

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert


async def upsert_place(
    session: AsyncSession,
    *,
    google_place_id: str,
    name: str,
    formatted_address: str | None,
    lat: float,
    lon: float,
    google_types: list[str],
) -> "Place":
    """Insert-or-update a place by `google_place_id`. Returns the live row."""
    from app.db.models import Place

    stmt = (
        pg_insert(Place)
        .values(
            google_place_id=google_place_id,
            name=name,
            formatted_address=formatted_address,
            location=f"SRID=4326;POINT({lon} {lat})",
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
```

### 5. Add a `recompute_aggregates` helper

A single SQL update. Called inside the `/verify` transaction in phase 03 so
the place's denormalised counters are always consistent with its child rows.
Uses a recency-weighted mean: contributions in the last 180 days have weight
1.0, decaying exponentially after that (half-life 180 days).

```python
async def recompute_place_aggregates(session: AsyncSession, place_id: UUID) -> None:
    """Recompute contribution_count, public_count, aggregate_trust, last_contribution_at."""
    await session.execute(
        text("""
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
                    WHEN COUNT(*) FILTER (WHERE visibility_status = 'PUBLIC') = 0 THEN 0.0
                    ELSE
                      SUM(trust_score * EXP(-LN(2) * EXTRACT(EPOCH FROM (now() - created_at)) / (180 * 86400)))
                      FILTER (WHERE visibility_status = 'PUBLIC')
                      /
                      SUM(EXP(-LN(2) * EXTRACT(EPOCH FROM (now() - created_at)) / (180 * 86400)))
                      FILTER (WHERE visibility_status = 'PUBLIC')
                END AS weighted_trust
            FROM contributions
            WHERE place_id = :pid
        ) stats
        WHERE p.id = :pid
        """),
        {"pid": str(place_id)},
    )
```

### 6. Update `Settings` for the recency half-life (optional — keep hard-coded 180d if you prefer)

Skip if you don't want to expose this knob.

---

## Acceptance criteria

- [ ] `alembic upgrade head` applies cleanly on a fresh DB.
- [ ] `alembic downgrade base` then `upgrade head` round-trips with no errors.
- [ ] `\d places` and `\d contributions` in psql show the new columns and FK.
- [ ] `SELECT * FROM places LIMIT 0;` succeeds.
- [ ] Spatial helper `find_nearby_places` returns `[]` (not crash) with no data.
- [ ] Existing tests still pass: `cd backend && python -m pytest -q`.

## Smoke commands

```bash
# 1. Spin up clean DB and run all migrations
docker compose down -v && docker compose up -d
sleep 8
cd backend && alembic upgrade head

# 2. Verify schema
docker exec naviable-postgis psql -U naviable -d naviable -c "\dt"
docker exec naviable-postgis psql -U naviable -d naviable -c "\d places"
docker exec naviable-postgis psql -U naviable -d naviable -c "\d contributions"
docker exec naviable-postgis psql -U naviable -d naviable -c "\d training_exports"

# 3. Round-trip down/up
alembic downgrade -1 && alembic upgrade head

# 4. Existing test suite still green
cd backend && python -m pytest -q
```

## Pitfalls

- The Postgres port mapping in `docker-compose.yml` is currently `5434:5432`.
  The default `database_url` in settings is `localhost:5434/naviable`. Don't
  change it without updating both.
- `geoalchemy2.Geometry` autogen is flaky — if alembic emits something
  weird like `sa.NullType`, hand-edit the migration to use `Geometry(...)`.
- The `gen_random_uuid()` server default needs the `pgcrypto` extension. The
  initial migration already creates `postgis` and `postgis_topology`; it
  should also `CREATE EXTENSION IF NOT EXISTS pgcrypto;`. If your initial
  migration doesn't, add it.
