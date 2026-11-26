from typing import Annotated

from fastapi import Depends

from app.wishlists.service import Service

SvcDep = Annotated[Service, Depends()]
