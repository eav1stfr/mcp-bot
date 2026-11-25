from app.common.models import AbstractSchema


class UserRetrieve(AbstractSchema):
    id: int
    name: str


class CoupleRetrieve(AbstractSchema):
    me: UserRetrieve
    partner: UserRetrieve
