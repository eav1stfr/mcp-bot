from app.common.dependencies import DBSessionDep
from app.common.exceptions import Forbidden, NotFound
from app.users.constants import Person
from app.users.models import User
from app.users.schemas import UserRetrieve
from app.users.service import Service as UsersService
from app.wishlists.constants import WishlistErrorMessage
from app.wishlists.models import WishlistItem
from app.wishlists.repository import WishlistItemRepository
from app.wishlists.schemas import (
    MultipleWishlistItemsRetrieve,
    WishlistItemCreateRequest,
    WishlistItemRetrieve,
    WishlistItemUpdateRequest,
)


class Service:
    """Service layer for wishlists: both may read, only owners may change"""

    def __init__(self, session: DBSessionDep):
        self.item_repo = WishlistItemRepository(session)
        self.users_svc = UsersService(session)

    def get_wishlist(
        self, actor: User, person: Person
    ) -> MultipleWishlistItemsRetrieve:
        owner = self.users_svc.resolve(actor, person)
        items = self.item_repo.get_by_owner(owner.id)
        return MultipleWishlistItemsRetrieve(
            owner=UserRetrieve(id=owner.id, name=owner.name),
            items=[self._retrieve(item) for item in items],
            count=len(items),
        )

    def add_item(
        self, actor: User, data: WishlistItemCreateRequest
    ) -> WishlistItemRetrieve:
        """Add an item to the actor's own wishlist"""
        item = WishlistItem(owner_id=actor.id, **data.model_dump())
        return self._retrieve(self.item_repo.create(item))

    def update_item(
        self, actor: User, item_id: int, data: WishlistItemUpdateRequest
    ) -> WishlistItemRetrieve:
        item = self._get_own_item(actor, item_id)
        item.sqlmodel_update(data.model_dump(exclude_unset=True))
        return self._retrieve(self.item_repo.update(item))

    def delete_item(self, actor: User, item_id: int) -> None:
        item = self._get_own_item(actor, item_id)
        self.item_repo.delete(item.id)

    def _get_own_item(self, actor: User, item_id: int) -> WishlistItem:
        item = self.item_repo.get(item_id)
        if item is None:
            raise NotFound(WishlistErrorMessage.ITEM_NOT_FOUND)
        if item.owner_id != actor.id:
            raise Forbidden(WishlistErrorMessage.NOT_OWNER)
        return item

    @staticmethod
    def _retrieve(item: WishlistItem) -> WishlistItemRetrieve:
        return WishlistItemRetrieve.model_validate(item, from_attributes=True)
