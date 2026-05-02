"""initial: postgis extension + contributions table

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")  # provides gen_random_uuid

    op.create_table(
        "contributions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("image_path", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("image_phash", sa.BigInteger(), nullable=True),
        sa.Column("text_note", sa.Text(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("vision_score", sa.REAL(), nullable=False),
        sa.Column("nlp_score", sa.REAL(), nullable=False),
        sa.Column("trust_score", sa.REAL(), nullable=False),
        sa.Column("visibility_status", sa.String(length=16), nullable=False),
        sa.Column(
            "detected_features",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="contributions_rating_range"),
        sa.CheckConstraint(
            "vision_score BETWEEN 0 AND 1", name="contributions_vision_range"
        ),
        sa.CheckConstraint("nlp_score BETWEEN 0 AND 1", name="contributions_nlp_range"),
        sa.CheckConstraint(
            "trust_score BETWEEN 0 AND 1", name="contributions_trust_range"
        ),
        sa.CheckConstraint(
            "visibility_status IN ('PUBLIC','CAVEAT','HIDDEN')",
            name="contributions_visibility_enum",
        ),
    )

    op.create_index(
        "contributions_location_gix",
        "contributions",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index(
        "contributions_status_idx",
        "contributions",
        ["visibility_status"],
    )


def downgrade() -> None:
    op.drop_index("contributions_status_idx", table_name="contributions")
    op.drop_index("contributions_location_gix", table_name="contributions")
    op.drop_table("contributions")
