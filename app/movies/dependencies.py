from typing import Annotated

from fastapi import Depends

from app.movies.service import Service

SvcDep = Annotated[Service, Depends()]
