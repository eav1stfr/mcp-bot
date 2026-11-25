from app.common.dependencies import DBSessionDep
from app.common.exceptions import InternalError, Unauthorized
from app.users.constants import Person, UserErrorMessage
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import CoupleRetrieve, UserRetrieve


class Service:
    """Service layer for the two users and who is me or partner"""

    def __init__(self, session: DBSessionDep):
        self.user_repo = UserRepository(session)

    def get_by_telegram_id(self, telegram_id: int) -> User:
        """The user with this Telegram ID; anyone else is refused"""
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise Unauthorized(UserErrorMessage.UNKNOWN_USER)
        return user

    def get_partner(self, actor: User) -> User:
        partner = None
        if actor.partner_id:
            partner = self.user_repo.get(actor.partner_id)
        if partner is None:
            # Both users are seeded together, so this is a setup error
            raise InternalError(UserErrorMessage.NO_PARTNER)
        return partner

    def resolve(self, actor: User, person: Person) -> User:
        """The user that `person` means from the actor's point of view"""
        if person == Person.ME:
            return actor
        return self.get_partner(actor)

    def get_couple(self, actor: User) -> CoupleRetrieve:
        partner = self.get_partner(actor)
        return CoupleRetrieve(
            me=UserRetrieve(id=actor.id, name=actor.name),
            partner=UserRetrieve(id=partner.id, name=partner.name),
        )
