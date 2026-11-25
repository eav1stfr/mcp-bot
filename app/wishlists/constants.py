from enum import StrEnum

LINK_MAX_LENGTH = 2048


class WishlistErrorMessage(StrEnum):
    ITEM_NOT_FOUND = "Wishlist item not found"
    NOT_OWNER = "Only the owner can change their wishlist"
