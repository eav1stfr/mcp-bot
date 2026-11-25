from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field, field_validator

from app.common.models import AbstractSchema
from app.users.schemas import UserRetrieve
from app.wishlists.constants import LINK_MAX_LENGTH
from app.wishlists.utils import validate_link

Link = Annotated[
    str, Field(max_length=LINK_MAX_LENGTH), AfterValidator(validate_link)
]


class WishlistItemBase(AbstractSchema):
    title: str = Field(min_length=1, max_length=200)
    link: Link | None = None
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    note: str | None = Field(default=None, max_length=1000)


class WishlistItemCreateRequest(WishlistItemBase):
    pass


class WishlistItemUpdateRequest(AbstractSchema):
    """Only the fields sent are changed; null clears an optional field"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    link: Link | None = None
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("title")
    @classmethod
    def title_is_not_cleared(cls, title: str | None) -> str:
        if title is None:
            raise ValueError("title can't be null")
        return title


class WishlistItemRetrieve(AbstractSchema):
    id: int
    owner_id: int
    title: str
    link: str | None
    price: Decimal | None
    note: str | None
    created_at: datetime
    updated_at: datetime


class MultipleWishlistItemsRetrieve(AbstractSchema):
    owner: UserRetrieve
    items: list[WishlistItemRetrieve]
    count: int
