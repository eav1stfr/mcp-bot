from fastapi import APIRouter, status

from app.actions.constants import ActionPrice, ActionSetting, ActionStatus
from app.actions.dependencies import SvcDep
from app.actions.schemas import (
    ActionCreateRequest,
    ActionRetrieve,
    ActionUpdateRequest,
    MultipleActionsRetrieve,
)
from app.users.dependencies import ActorDep, IsKnownUser

actions_router = APIRouter(prefix="/actions", tags=["actions"])


@actions_router.get(
    "",
    dependencies=[IsKnownUser],
    summary="The shared list of date ideas",
    description=(
        "Filters combine; any filter left out matches everything. Ideas "
        "without a setting or price only show up when that filter is "
        "left out."
    ),
)
def list_actions(
    svc: SvcDep,
    status: ActionStatus | None = None,
    setting: ActionSetting | None = None,
    price: ActionPrice | None = None,
) -> MultipleActionsRetrieve:
    return svc.list_actions(status, setting, price)


@actions_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a date idea",
)
def add_action(
    svc: SvcDep, actor: ActorDep, request: ActionCreateRequest
) -> ActionRetrieve:
    return svc.add_action(actor, request)


@actions_router.patch(
    "/{action_id}",
    dependencies=[IsKnownUser],
    summary="Edit a date idea or mark it done",
)
def update_action(
    svc: SvcDep, action_id: int, request: ActionUpdateRequest
) -> ActionRetrieve:
    return svc.update_action(action_id, request)


@actions_router.delete(
    "/{action_id}",
    dependencies=[IsKnownUser],
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a date idea",
)
def delete_action(svc: SvcDep, action_id: int) -> None:
    svc.delete_action(action_id)
