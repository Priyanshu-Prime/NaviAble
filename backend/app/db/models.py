"""SQLAlchemy ORM models for NaviAble.

The single canonical table is ``contributions`` — every photo + review pair
that passes through ``POST /api/v1/verify`` lands here. Low-confidence rows
are retained with ``visibility_status='HIDDEN'`` rather than deleted, so
future re-evaluation is possible.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import CheckConstraint, Index, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Contribution(Base):
    __tablename__ = "contributions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_phash: Mapped[int | None] = mapped_column(nullable=True)
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
    )
