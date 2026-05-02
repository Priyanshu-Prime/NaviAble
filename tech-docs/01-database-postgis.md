# Phase 01 — Database & PostGIS

## Goal

Stand up a PostgreSQL database with the PostGIS extension enabled, define the
`contributions` table that the entire backend reads and writes, create a
spatial (GIST) index that makes "find within X metres" queries cheap, and
ship a small set of helpers that the FastAPI layer in phase 02 will import.

This phase is foundational — every later backend phase reads or writes
through this schema. Get it right before moving on.

## Prerequisites

- Docker (preferred) or local Postgres 14+ with PostGIS 3+ installed.
- Python 3.11 in `.venv` with `psycopg[binary]` and `SQLAlchemy>=2.0`.

## Current state

- No `contributions` table exists yet.
- `backend/app/services/ml.py` already exists; the DB layer it will write to
  does not.
- `backend/uploads/` directory is committed for storing image files
  referenced by `image_path`.

## Deliverables

### 1. Local Postgres + PostGIS via Docker Compose

Add `docker-compose.yml` at repo root (or under `backend/`) with a
`postgis/postgis:16-3.4` image. Persist data to a named volume.
Expose port `5432`.

Environment variables to standardise on:

```
POSTGRES_USER=naviable
POSTGRES_PASSWORD=naviable_dev
POSTGRES_DB=naviable
DATABASE_URL=postgresql+psycopg://naviable:naviable_dev@localhost:5432/naviable
```

`.env.example` at repo root must list these so a fresh clone can boot.

### 2. Schema migration

Use Alembic for migrations. Initial migration must:

1. `CREATE EXTENSION IF NOT EXISTS postgis;`
2. Create the `contributions` table:

| Column              | Type                            | Notes                                         |
|---------------------|---------------------------------|-----------------------------------------------|
| `id`                | `UUID PRIMARY KEY`              | Default `gen_random_uuid()`                   |
| `location`          | `geometry(Point, 4326) NOT NULL`| WGS84 lon/lat                                 |
| `image_path`        | `text NOT NULL`                 | Local path or object-store key                |
| `image_url`         | `text`                          | Public URL when served, nullable              |
| `image_phash`       | `bigint`                        | Perceptual hash; used by vision cache         |
| `text_note`         | `text NOT NULL`                 | Review body; reject empty upstream            |
| `rating`            | `smallint NOT NULL`             | `CHECK (rating BETWEEN 1 AND 5)`              |
| `vision_score`      | `real NOT NULL`                 | `CHECK (vision_score BETWEEN 0 AND 1)`        |
| `nlp_score`         | `real NOT NULL`                 | `CHECK (nlp_score BETWEEN 0 AND 1)`           |
| `trust_score`       | `real NOT NULL`                 | `CHECK (trust_score BETWEEN 0 AND 1)`         |
| `visibility_status` | `text NOT NULL`                 | `CHECK (visibility_status IN ('PUBLIC','CAVEAT','HIDDEN'))` |
| `detected_features` | `jsonb NOT NULL DEFAULT '{}'`   | Per-class confidences + boxes from YOLO       |
| `created_at`        | `timestamptz NOT NULL`          | Default `now()`                               |

3. `CREATE INDEX contributions_location_gix ON contributions USING GIST (location);`
4. `CREATE INDEX contributions_status_idx ON contributions (visibility_status);`
   — discovery queries filter on this constantly.

### 3. SQLAlchemy model

`backend/app/db/models.py`:

```python
from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
# ...
class Contribution(Base):
    __tablename__ = "contributions"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    location: Mapped[WKBElement] = mapped_column(Geometry("POINT", srid=4326))
    # ...
```

Use `geoalchemy2` for the Geometry column. Do not roll your own WKT parsing.

### 4. Spatial query helper

`backend/app/db/queries.py` exposes one function that the discovery endpoint
in phase 07 will call:

```python
async def find_nearby(
    session: AsyncSession,
    *,
    lat: float,
    lon: float,
    radius_m: float,
    include_caveat: bool = True,
    limit: int = 200,
) -> list[Contribution]:
    """Return public (and optionally caveat) contributions within radius_m."""
```

It must:
- Use `ST_DWithin(location::geography, ST_MakePoint(:lon,:lat)::geography, :radius_m)`
  so the radius is interpreted in metres regardless of latitude. (Plain
  `ST_DWithin` on `geometry` uses the SRID's units, which for SRID 4326 is
  degrees — wrong.)
- Filter `visibility_status = 'PUBLIC'` always; include `'CAVEAT'` when
  `include_caveat`. **Never** return `HIDDEN`.
- Be ordered by distance ascending.
- Cap at `limit` rows.

### 5. Connection plumbing

- `backend/app/db/session.py` exposes an async `engine` and a
  `get_session` FastAPI dependency.
- Connection pool sized modestly (e.g. `pool_size=5, max_overflow=10`) — the
  workload is I/O bound on model inference, not DB.

## Acceptance criteria

- [ ] `docker compose up -d` brings up Postgres+PostGIS locally.
- [ ] `alembic upgrade head` from a fresh DB creates the `contributions`
      table with all constraints, indexes, and the PostGIS extension.
- [ ] `psql` shows `\d contributions` matches the table above exactly.
- [ ] A unit test inserts three fixture rows at known lat/lon and
      `find_nearby` returns the expected subset for a 500 m radius.
- [ ] A `HIDDEN` row is never returned by `find_nearby`, even when the
      caller passes a wide radius.
- [ ] `EXPLAIN ANALYZE` on `find_nearby` shows the GIST index in use
      (Index Scan, not Seq Scan) once the table holds >1 000 rows.

## Pitfalls / notes

- **SRID matters.** Store as `Geometry(Point, 4326)`. If you cast to
  `geography` for distance, do it inside the query, not on the column type
  — `geography` distance is always metres but `geography` indexing has
  worse selectivity for small radii.
- **Don't over-design tags now.** A `tags` column for individual feature
  types (ramp, stairs, etc.) is tempting; keep them inside
  `detected_features` JSONB for now. If the discovery view starts needing
  to filter by feature type, add a normalised side table later.
- The `image_phash` column is populated by the vision wrapper (phase 03),
  not at the API edge. It exists here so vision can de-dup *across*
  contributions, not just within a process lifetime.
