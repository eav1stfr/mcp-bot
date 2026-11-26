from datetime import datetime

from sqlalchemy import CheckConstraint, SmallInteger, UniqueConstraint, text
from sqlmodel import Column, Field, ForeignKey

from app.common.models import Model
from app.movies.constants import MAX_SCORE, MIN_SCORE, MovieStatus


class Movie(Model, table=True):
    """A movie on the shared list; either user may change it"""
    __tablename__ = "movies"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, max_length=200)
    year: int | None = Field(default=None)
    note: str | None = Field(default=None, max_length=1000)
    added_by: int | None = Field(
        default=None,
        sa_column=Column(
            # The list is shared, so it outlives whoever added the movie
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        )
    )
    status: MovieStatus = Field(
        default=MovieStatus.TO_WATCH, nullable=False, index=True
    )
    watched_at: datetime | None = Field(default=None)
    created_at: datetime = Field(
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )


class MovieRating(Model, table=True):
    """One user's score for a movie; each user has at most one per movie"""
    __tablename__ = "movie_ratings"

    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(
        sa_column=Column(
            ForeignKey("movies.id", ondelete="CASCADE"),
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
    comment: str | None = Field(default=None, max_length=1000)
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
            "movie_id", "user_id", name="uq_movie_ratings_movie_id_user_id"
        ),
        CheckConstraint(
            f"score BETWEEN {MIN_SCORE} AND {MAX_SCORE}",
            name="ck_movie_ratings_score_range",
        ),
    )
