from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict
from sqlmodel import SQLModel


def convert_datetime_to_gmt(dt: datetime) -> str:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=UTC)

    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


def convert_date_to_format(d: date) -> str:
    return d.strftime("%Y-%m-%d")


class AbstractSchema(BaseModel):
    """Base class for Pydantic schemas within the app."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_encoders={
            datetime: convert_datetime_to_gmt,
            date: convert_date_to_format,
        },
    )


class Model(AbstractSchema, SQLModel):
    """Base model class for models within the app."""
