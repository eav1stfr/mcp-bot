from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.database import DB_ENGINE


def get_session() -> Generator[Session, None, None]:
    with Session(DB_ENGINE) as session:
        yield session


DBSessionDep = Annotated[Session, Depends(get_session)]
