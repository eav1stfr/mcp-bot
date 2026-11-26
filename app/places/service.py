from collections import defaultdict
from collections.abc import Sequence

from app.common.dependencies import DBSessionDep
from app.common.exceptions import NotFound
from app.common.utils import get_now_utc
from app.places.constants import PlaceErrorMessage, PlaceStatus
from app.places.models import Place, PlaceReview
from app.places.repository import PlaceRepository, PlaceReviewRepository
from app.places.schemas import (
    MultiplePlacesRetrieve,
    PlaceCreateRequest,
    PlaceRetrieve,
    PlaceReviewRequest,
    PlaceReviewRetrieve,
    PlaceUpdateRequest,
)
from app.users.models import User
from app.users.repository import UserRepository


class Service:
    """Service layer for the shared place list and each user's reviews"""

    def __init__(self, session: DBSessionDep):
        self.place_repo = PlaceRepository(session)
        self.review_repo = PlaceReviewRepository(session)
        self.user_repo = UserRepository(session)

    def list_places(self, status: PlaceStatus | None) -> MultiplePlacesRetrieve:
        """Places with both users' reviews; no status means all of them"""
        places = self.place_repo.get_list(status)
        return MultiplePlacesRetrieve(
            places=self._retrieve_many(places), count=len(places)
        )

    def add_place(self, actor: User, data: PlaceCreateRequest) -> PlaceRetrieve:
        place = Place(added_by=actor.id, **data.model_dump())
        return self._retrieve(self.place_repo.create(place))

    def update_place(
        self, place_id: int, data: PlaceUpdateRequest
    ) -> PlaceRetrieve:
        place = self._get_place(place_id)
        changes = data.model_dump(exclude_unset=True)
        status = changes.pop("status", None)
        place.sqlmodel_update(changes)
        if status is not None:
            self._set_status(place, status)
        return self._retrieve(self.place_repo.update(place))

    def delete_place(self, place_id: int) -> None:
        """Delete a place along with its reviews"""
        place = self._get_place(place_id)
        self.place_repo.delete(place.id)

    def review_place(
        self, actor: User, place_id: int, data: PlaceReviewRequest
    ) -> PlaceRetrieve:
        """Set the actor's own review; a reviewed place counts as visited"""
        place = self._get_place(place_id)
        review = self.review_repo.get_by_place_and_user(place.id, actor.id)
        if review is None:
            review = PlaceReview(place_id=place.id, user_id=actor.id)
        review.sqlmodel_update(data.model_dump())
        self.review_repo.update_without_commit(review)

        self._set_status(place, PlaceStatus.VISITED)
        self.place_repo.update_without_commit(place)
        self.place_repo.commit()
        return self._retrieve(place)

    def _get_place(self, place_id: int) -> Place:
        place = self.place_repo.get(place_id)
        if place is None:
            raise NotFound(PlaceErrorMessage.PLACE_NOT_FOUND)
        return place

    @staticmethod
    def _set_status(place: Place, status: PlaceStatus) -> None:
        """Change the status and keep visited_at in step with it"""
        if status == PlaceStatus.WANT_TO_VISIT:
            place.visited_at = None
        elif place.visited_at is None:
            place.visited_at = get_now_utc()
        place.status = status

    def _retrieve(self, place: Place) -> PlaceRetrieve:
        return self._retrieve_many([place])[0]

    def _retrieve_many(self, places: Sequence[Place]) -> list[PlaceRetrieve]:
        """Attach reviews and reviewers' names with two queries in total"""
        reviews = self.review_repo.get_for_places([p.id for p in places])
        reviewers = self.user_repo.get_many({r.user_id for r in reviews})

        reviews_by_place: dict[int, list[PlaceReviewRetrieve]] = defaultdict(
            list
        )
        for review in reviews:
            reviews_by_place[review.place_id].append(
                PlaceReviewRetrieve(
                    user_id=review.user_id,
                    user_name=reviewers[review.user_id].name,
                    score=review.score,
                    feedback=review.feedback,
                    updated_at=review.updated_at,
                )
            )
        return [
            PlaceRetrieve(
                **place.model_dump(), reviews=reviews_by_place[place.id]
            )
            for place in places
        ]
