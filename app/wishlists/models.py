from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Column, Field, ForeignKey

from app.common.models import Model
from app.wishlists.constants import LINK_MAX_LENGTH


class WishlistItem(Model, table=True):
    """Something one user wishes for; only its owner may change it"""
    __tablename__ = "wishlist_items"

    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            index=True,
            nullable=False
        )
    )
    title: str = Field(nullable=False, max_length=200)
    link: str | None = Field(default=None, max_length=LINK_MAX_LENGTH)
    price: Decimal | None = Field(
        default=None, max_digits=12, decimal_places=2
    )
    note: str | None = Field(default=None, max_length=1000)
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
