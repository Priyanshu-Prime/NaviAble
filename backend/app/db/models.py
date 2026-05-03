"""SQLAlchemy ORM models for NaviAble.

Three tables:

  places            — keyed by Google Places ``place_id``. Holds denormalised
                      aggregates (running mean trust, contribution count) so
                      the map view can colour markers in a single query.
  contributions     — every photo+review pair. Links to a ``places`` row.
                      Low-trust rows are kept with ``visibility_status=HIDDEN``
                      rather than deleted, so future re-evaluation is possible.
  training_exports  — bookkeeping for retraining cycles: which contributions
                      were folded into which model version, when.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
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
    """Declarative base for all ORM models."""


class Place(Base):
    """A real-world location, keyed by Google Places ``place_id``."""

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
    google_types: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )

    # Denormalised aggregates — recomputed inside the verify transaction.
    contribution_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    public_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    aggregate_trust: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("0.0"),
    )
    last_contribution_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )

    contributions: Mapped[list["Contribution"]] = relationship(
        back_populates="place",
        cascade="save-update",
    )

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
    # Nullable so legacy rows survive the migration; new rows always set this.
    place_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_phash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    text_note: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    vision_score: Mapped[float] = mapped_column(Float, nullable=False)
    nlp_score: Mapped[float] = mapped_column(Float, nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False)
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
        CheckConstraint(
            "vision_score BETWEEN 0 AND 1", name="contributions_vision_range"
        ),
        CheckConstraint("nlp_score BETWEEN 0 AND 1", name="contributions_nlp_range"),
        CheckConstraint(
            "trust_score BETWEEN 0 AND 1", name="contributions_trust_range"
        ),
        CheckConstraint(
            "visibility_status IN ('PUBLIC','CAVEAT','HIDDEN')",
            name="contributions_visibility_enum",
        ),
        Index(
            "contributions_location_gix",
            "location",
            postgresql_using="gist",
        ),
        Index("contributions_status_idx", "visibility_status"),
        Index("contributions_place_idx", "place_id"),
    )


class TrainingExport(Base):
    """One row per retraining dataset cut."""

    __tablename__ = "training_exports"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    export_path: Mapped[str] = mapped_column(Text, nullable=False)
    cutoff_started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    cutoff_ended_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    contribution_count: Mapped[int] = mapped_column(Integer, nullable=False)
    yolo_image_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    roberta_row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
