from datetime import datetime

from sqlalchemy import text
from sqlmodel import Column, Field, ForeignKey

from app.actions.constants import ActionPrice, ActionSetting, ActionStatus
from app.common.models import Model


class Action(Model, table=True):
    """A date idea to do together; either user may change it"""
    __tablename__ = "actions"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, max_length=200)
    note: str | None = Field(default=None, max_length=1000)
    created_by: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        )
    )
    setting: ActionSetting | None = Field(default=None, index=True)
    price: ActionPrice | None = Field(default=None, index=True)
    status: ActionStatus = Field(
        default=ActionStatus.TODO, nullable=False, index=True
    )
    done_at: datetime | None = Field(default=None)
    created_at: datetime = Field(
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
