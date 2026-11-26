from collections.abc import Sequence

from sqlmodel import col, select

from app.common.repository import ModelRepository
from app.wishlists.models import WishlistItem


class WishlistItemRepository(ModelRepository[WishlistItem]):
    """Repository layer for wishlist items"""
    default_model = WishlistItem

    def get_by_owner(self, owner_id: int) -> Sequence[WishlistItem]:
        """A user's wishlist, newest first"""
        statement = (
            select(WishlistItem)
            .where(WishlistItem.owner_id == owner_id)
            .order_by(
                col(WishlistItem.created_at).desc(),
                col(WishlistItem.id).desc(),
            )
        )
        return self.session.exec(statement).all()
