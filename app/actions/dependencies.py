from typing import Annotated

from fastapi import Depends

from app.actions.service import Service

SvcDep = Annotated[Service, Depends()]
