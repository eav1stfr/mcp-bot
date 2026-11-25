from fastapi import APIRouter, status

from app.places.constants import PlaceStatus
from app.places.dependencies import SvcDep
from app.places.schemas import (
    MultiplePlacesRetrieve,
    PlaceCreateRequest,
    PlaceRetrieve,
    PlaceReviewRequest,
    PlaceUpdateRequest,
)
from app.users.dependencies import ActorDep, IsKnownUser

places_router = APIRouter(prefix="/places", tags=["places"])


@places_router.get(
    "",
    dependencies=[IsKnownUser],
    summary="The shared place list with both reviews",
    description="Without `status`, returns every place.",
)
def list_places(
    svc: SvcDep, status: PlaceStatus | None = None
) -> MultiplePlacesRetrieve:
    return svc.list_places(status)


@places_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a place to visit",
)
def add_place(
    svc: SvcDep, actor: ActorDep, request: PlaceCreateRequest
) -> PlaceRetrieve:
    return svc.add_place(actor, request)


@places_router.patch(
    "/{place_id}", dependencies=[IsKnownUser], summary="Edit a place"
)
def update_place(
    svc: SvcDep, place_id: int, request: PlaceUpdateRequest
) -> PlaceRetrieve:
    return svc.update_place(place_id, request)


@places_router.delete(
    "/{place_id}",
    dependencies=[IsKnownUser],
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a place and its reviews",
)
def delete_place(svc: SvcDep, place_id: int) -> None:
    svc.delete_place(place_id)


@places_router.put(
    "/{place_id}/review",
    summary="Set my review; marks the place as visited",
)
def review_place(
    svc: SvcDep, actor: ActorDep, place_id: int, request: PlaceReviewRequest
) -> PlaceRetrieve:
    return svc.review_place(actor, place_id, request)
