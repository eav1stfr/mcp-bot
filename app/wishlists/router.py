from fastapi import APIRouter, status

from app.users.constants import Person
from app.users.dependencies import ActorDep
from app.wishlists.dependencies import SvcDep
from app.wishlists.schemas import (
    MultipleWishlistItemsRetrieve,
    WishlistItemCreateRequest,
    WishlistItemRetrieve,
    WishlistItemUpdateRequest,
)

wishlists_router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@wishlists_router.get("", summary="My or my partner's wishlist")
def get_wishlist(
    svc: SvcDep, actor: ActorDep, person: Person = Person.ME
) -> MultipleWishlistItemsRetrieve:
    return svc.get_wishlist(actor, person)


@wishlists_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to my wishlist",
)
def add_wishlist_item(
    svc: SvcDep, actor: ActorDep, request: WishlistItemCreateRequest
) -> WishlistItemRetrieve:
    return svc.add_item(actor, request)


@wishlists_router.patch("/{item_id}", summary="Edit an item on my wishlist")
def update_wishlist_item(
    svc: SvcDep,
    actor: ActorDep,
    item_id: int,
    request: WishlistItemUpdateRequest,
) -> WishlistItemRetrieve:
    return svc.update_item(actor, item_id, request)


@wishlists_router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item from my wishlist",
)
def delete_wishlist_item(svc: SvcDep, actor: ActorDep, item_id: int) -> None:
    svc.delete_item(actor, item_id)
