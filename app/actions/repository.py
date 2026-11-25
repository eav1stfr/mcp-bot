from collections.abc import Sequence

from sqlmodel import col, select

from app.actions.constants import ActionPrice, ActionSetting, ActionStatus
from app.actions.models import Action
from app.common.repository import ModelRepository


class ActionRepository(ModelRepository[Action]):
    """Repository layer for date ideas"""
    default_model = Action

    def get_list(
        self,
        status: ActionStatus | None,
        setting: ActionSetting | None,
        price: ActionPrice | None,
    ) -> Sequence[Action]:
        """Open ideas first, newest first; then latest done first"""
        statement = select(Action)
        if status is not None:
            statement = statement.where(Action.status == status)
        if setting is not None:
            statement = statement.where(Action.setting == setting)
        if price is not None:
            statement = statement.where(Action.price == price)
        statement = statement.order_by(
            col(Action.status),
            col(Action.done_at).desc().nulls_last(),
            col(Action.created_at).desc(),
            col(Action.id).desc(),
        )
        return self.session.exec(statement).all()
