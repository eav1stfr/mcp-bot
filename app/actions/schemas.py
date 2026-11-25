from datetime import datetime

from pydantic import Field, field_validator

from app.actions.constants import ActionPrice, ActionSetting, ActionStatus
from app.common.models import AbstractSchema


class ActionBase(AbstractSchema):
    title: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=1000)
    setting: ActionSetting | None = None
    price: ActionPrice | None = None


class ActionCreateRequest(ActionBase):
    pass


class ActionUpdateRequest(AbstractSchema):
    """Only the fields sent are changed; null clears an optional field"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=1000)
    setting: ActionSetting | None = None
    price: ActionPrice | None = None
    status: ActionStatus | None = None

    @field_validator("title", "status")
    @classmethod
    def is_not_cleared[T](cls, value: T | None) -> T:
        if value is None:
            raise ValueError("can't be null")
        return value


class ActionRetrieve(AbstractSchema):
    id: int
    title: str
    note: str | None
    created_by: int | None
    setting: ActionSetting | None
    price: ActionPrice | None
    status: ActionStatus
    done_at: datetime | None
    created_at: datetime


class MultipleActionsRetrieve(AbstractSchema):
    actions: list[ActionRetrieve]
    count: int
