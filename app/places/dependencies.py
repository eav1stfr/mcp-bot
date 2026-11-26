from typing import Annotated

from fastapi import Depends

from app.places.service import Service

SvcDep = Annotated[Service, Depends()]
