from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field, field_validator

from app.common.models import AbstractSchema
from app.config.places_config import config
from app.places.constants import LINK_MAX_LENGTH, PlaceStatus
from app.places.utils import validate_link

Link = Annotated[
    str, Field(max_length=LINK_MAX_LENGTH), AfterValidator(validate_link)
]


class PlaceBase(AbstractSchema):
    title: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    link: Link | None = None
    note: str | None = Field(default=None, max_length=1000)


class PlaceCreateRequest(PlaceBase):
    pass


class PlaceUpdateRequest(AbstractSchema):
    """Only the fields sent are changed; null clears an optional field"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    link: Link | None = None
    note: str | None = Field(default=None, max_length=1000)
    status: PlaceStatus | None = None

    @field_validator("title", "status")
    @classmethod
    def is_not_cleared[T](cls, value: T | None) -> T:
        if value is None:
            raise ValueError("can't be null")
        return value


class PlaceReviewRequest(AbstractSchema):
    """The caller's own review; sending it again replaces it"""
    score: int = Field(ge=config.PLACE_MIN_SCORE, le=config.PLACE_MAX_SCORE)
    feedback: str | None = Field(default=None, max_length=1000)


class PlaceReviewRetrieve(AbstractSchema):
    user_id: int
    user_name: str
    score: int
    feedback: str | None
    updated_at: datetime


class PlaceRetrieve(AbstractSchema):
    id: int
    title: str
    location: str | None
    link: str | None
    note: str | None
    added_by: int | None
    status: PlaceStatus
    visited_at: datetime | None
    created_at: datetime
    reviews: list[PlaceReviewRetrieve]


class MultiplePlacesRetrieve(AbstractSchema):
    places: list[PlaceRetrieve]
    count: int
