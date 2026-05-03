"""places + contributions.place_id FK + training_exports

Revision ID: 0002_places_and_training_exports
Revises: 0001_initial
Create Date: 2026-05-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql


revision = "0002_places_and_training_exports"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── places ────────────────────────────────────────────────────────────
    op.create_table(
        "places",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("google_place_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("formatted_address", sa.Text(), nullable=True),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column(
            "google_types",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "contribution_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "public_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "aggregate_trust",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "last_contribution_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "aggregate_trust BETWEEN 0 AND 1",
            name="places_trust_range",
        ),
        sa.UniqueConstraint("google_place_id", name="places_google_place_id_key"),
    )
    op.create_index(
        "places_location_gix",
        "places",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_places_google_place_id",
        "places",
        ["google_place_id"],
    )

    # ── contributions.place_id FK ─────────────────────────────────────────
    op.add_column(
        "contributions",
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_contributions_place_id",
        "contributions",
        "places",
        ["place_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "contributions_place_idx",
        "contributions",
        ["place_id"],
    )

    # ── training_exports ──────────────────────────────────────────────────
    op.create_table(
        "training_exports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("export_path", sa.Text(), nullable=False),
        sa.Column(
            "cutoff_started_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "cutoff_ended_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("contribution_count", sa.Integer(), nullable=False),
        sa.Column(
            "yolo_image_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "roberta_row_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("training_exports")
    op.drop_index("contributions_place_idx", table_name="contributions")
    op.drop_constraint(
        "fk_contributions_place_id", "contributions", type_="foreignkey",
    )
    op.drop_column("contributions", "place_id")
    op.drop_index("ix_places_google_place_id", table_name="places")
    op.drop_index("places_location_gix", table_name="places")
    op.drop_table("places")
