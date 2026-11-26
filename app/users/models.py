from datetime import datetime

from sqlalchemy import BigInteger, text
from sqlmodel import Column, Field, ForeignKey

from app.common.models import Model


class User(Model, table=True):
    """One of the two people using the bot"""
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    telegram_id: int = Field(
        sa_column=Column(BigInteger, unique=True, nullable=False)
    )
    name: str = Field(nullable=False, max_length=64)
    partner_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        )
    )
    created_at: datetime = Field(
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
