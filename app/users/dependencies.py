from typing import Annotated

from fastapi import Depends, Header

from app.users.models import User
from app.users.service import Service

SvcDep = Annotated[Service, Depends()]


def get_actor(
    svc: SvcDep, x_telegram_user_id: Annotated[int, Header()]
) -> User:
    """The user making the request, named by the X-Telegram-User-Id header"""
    return svc.get_by_telegram_id(x_telegram_user_id)


ActorDep = Annotated[User, Depends(get_actor)]
IsKnownUser = Depends(get_actor)
"""For routes that don't need the actor but must refuse strangers"""
