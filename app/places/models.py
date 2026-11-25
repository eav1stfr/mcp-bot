from datetime import datetime

from sqlalchemy import CheckConstraint, SmallInteger, UniqueConstraint, text
from sqlmodel import Column, Field, ForeignKey

from app.common.models import Model
from app.config.places_config import config
from app.places.constants import LINK_MAX_LENGTH, PlaceStatus


class Place(Model, table=True):
    """A place on the shared list; either user may change it"""
    __tablename__ = "places"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    link: str | None = Field(default=None, max_length=LINK_MAX_LENGTH)
    note: str | None = Field(default=None, max_length=1000)
    added_by: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        )
    )
    status: PlaceStatus = Field(
        default=PlaceStatus.WANT_TO_VISIT, nullable=False, index=True
    )
    visited_at: datetime | None = Field(default=None)
    created_at: datetime = Field(
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )


class PlaceReview(Model, table=True):
    """One user's review of a place; each user has at most one per place"""
    __tablename__ = "place_reviews"

    id: int | None = Field(default=None, primary_key=True)
    place_id: int = Field(
        sa_column=Column(
            ForeignKey("places.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    user_id: int = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    score: int = Field(sa_column=Column(SmallInteger, nullable=False))
    feedback: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    updated_at: datetime = Field(
        nullable=False,
        sa_column_kwargs={
            "onupdate": text("CURRENT_TIMESTAMP"),
            "server_default": text("CURRENT_TIMESTAMP")
        }
    )

    __table_args__ = (
        UniqueConstraint(
            "place_id", "user_id", name="uq_place_reviews_place_id_user_id"
        ),
        CheckConstraint(
            f"score BETWEEN {config.PLACE_MIN_SCORE}"
            f" AND {config.PLACE_MAX_SCORE}",
            name="ck_place_reviews_score_range",
        ),
    )
