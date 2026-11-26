from collections.abc import Collection, Sequence

from sqlmodel import col, select

from app.common.repository import ModelRepository
from app.places.constants import PlaceStatus
from app.places.models import Place, PlaceReview


class PlaceRepository(ModelRepository[Place]):
    """Repository layer for places"""
    default_model = Place

    def get_list(self, status: PlaceStatus | None) -> Sequence[Place]:
        """Unvisited first, newest added first; then latest visited first"""
        statement = select(Place)
        if status is not None:
            statement = statement.where(Place.status == status)
        statement = statement.order_by(
            col(Place.status),
            col(Place.visited_at).desc().nulls_last(),
            col(Place.created_at).desc(),
            col(Place.id).desc(),
        )
        return self.session.exec(statement).all()


class PlaceReviewRepository(ModelRepository[PlaceReview]):
    """Repository layer for place reviews"""
    default_model = PlaceReview

    def get_for_places(
        self, place_ids: Collection[int]
    ) -> Sequence[PlaceReview]:
        """Reviews of several places in one query, oldest first"""
        statement = (
            select(PlaceReview)
            .where(col(PlaceReview.place_id).in_(place_ids))
            .order_by(col(PlaceReview.created_at), col(PlaceReview.id))
        )
        return self.session.exec(statement).all()

    def get_by_place_and_user(
        self, place_id: int, user_id: int
    ) -> PlaceReview | None:
        statement = select(PlaceReview).where(
            PlaceReview.place_id == place_id,
            PlaceReview.user_id == user_id,
        )
        return self.session.exec(statement).first()
