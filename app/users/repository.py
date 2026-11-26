from collections.abc import Collection

from sqlmodel import col, select

from app.common.repository import ModelRepository
from app.users.models import User


class UserRepository(ModelRepository[User]):
    """Repository layer for users"""
    default_model = User

    def get_by_telegram_id(self, telegram_id: int) -> User | None:
        statement = select(User).where(User.telegram_id == telegram_id)
        return self.session.exec(statement).first()

    def get_many(self, ids: Collection[int]) -> dict[int, User]:
        """Users by id, for attaching names without a query per row"""
        statement = select(User).where(col(User.id).in_(ids))
        return {user.id: user for user in self.session.exec(statement)}
