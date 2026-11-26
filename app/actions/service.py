from app.actions.constants import (
    ActionErrorMessage,
    ActionPrice,
    ActionSetting,
    ActionStatus,
)
from app.actions.models import Action
from app.actions.repository import ActionRepository
from app.actions.schemas import (
    ActionCreateRequest,
    ActionRetrieve,
    ActionUpdateRequest,
    MultipleActionsRetrieve,
)
from app.common.dependencies import DBSessionDep
from app.common.exceptions import NotFound
from app.common.utils import get_now_utc
from app.users.models import User


class Service:
    """Service layer for the shared list of date ideas"""

    def __init__(self, session: DBSessionDep):
        self.action_repo = ActionRepository(session)

    def list_actions(
        self,
        status: ActionStatus | None,
        setting: ActionSetting | None,
        price: ActionPrice | None,
    ) -> MultipleActionsRetrieve:
        """Ideas matching every filter given; no filters means all"""
        actions = self.action_repo.get_list(status, setting, price)
        return MultipleActionsRetrieve(
            actions=[self._retrieve(action) for action in actions],
            count=len(actions),
        )

    def add_action(
        self, actor: User, data: ActionCreateRequest
    ) -> ActionRetrieve:
        action = Action(created_by=actor.id, **data.model_dump())
        return self._retrieve(self.action_repo.create(action))

    def update_action(
        self, action_id: int, data: ActionUpdateRequest
    ) -> ActionRetrieve:
        action = self._get_action(action_id)
        changes = data.model_dump(exclude_unset=True)
        status = changes.pop("status", None)
        action.sqlmodel_update(changes)
        if status is not None:
            self._set_status(action, status)
        return self._retrieve(self.action_repo.update(action))

    def delete_action(self, action_id: int) -> None:
        action = self._get_action(action_id)
        self.action_repo.delete(action.id)

    def _get_action(self, action_id: int) -> Action:
        action = self.action_repo.get(action_id)
        if action is None:
            raise NotFound(ActionErrorMessage.ACTION_NOT_FOUND)
        return action

    @staticmethod
    def _set_status(action: Action, status: ActionStatus) -> None:
        """Change the status and keep done_at in step with it"""
        if status == ActionStatus.TODO:
            action.done_at = None
        elif action.done_at is None:
            action.done_at = get_now_utc()
        action.status = status

    @staticmethod
    def _retrieve(action: Action) -> ActionRetrieve:
        return ActionRetrieve.model_validate(action, from_attributes=True)
