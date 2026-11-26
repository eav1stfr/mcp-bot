from datetime import datetime

from pydantic import Field, field_validator

from app.common.models import AbstractSchema
from app.movies.constants import (
    MAX_SCORE,
    MAX_YEAR,
    MIN_SCORE,
    MIN_YEAR,
    MovieStatus,
)


class MovieBase(AbstractSchema):
    title: str = Field(min_length=1, max_length=200)
    year: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR)
    note: str | None = Field(default=None, max_length=1000)


class MovieCreateRequest(MovieBase):
    pass


class MovieUpdateRequest(AbstractSchema):
    """Only the fields sent are changed; null clears year or note"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    year: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR)
    note: str | None = Field(default=None, max_length=1000)
    status: MovieStatus | None = None

    @field_validator("title", "status")
    @classmethod
    def is_not_cleared[T](cls, value: T | None) -> T:
        if value is None:
            raise ValueError("can't be null")
        return value


class MovieRatingRequest(AbstractSchema):
    """The caller's own rating; sending it again replaces it"""
    score: int = Field(ge=MIN_SCORE, le=MAX_SCORE)
    comment: str | None = Field(default=None, max_length=1000)


class MovieRatingRetrieve(AbstractSchema):
    user_id: int
    user_name: str
    score: int
    comment: str | None
    updated_at: datetime


class MovieRetrieve(AbstractSchema):
    id: int
    title: str
    year: int | None
    note: str | None
    added_by: int | None
    status: MovieStatus
    watched_at: datetime | None
    created_at: datetime
    ratings: list[MovieRatingRetrieve]


class MultipleMoviesRetrieve(AbstractSchema):
    movies: list[MovieRetrieve]
    count: int
