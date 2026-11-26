from collections.abc import Collection, Sequence

from sqlmodel import col, select

from app.common.repository import ModelRepository
from app.movies.constants import MovieStatus
from app.movies.models import Movie, MovieRating


class MovieRepository(ModelRepository[Movie]):
    """Repository layer for movies"""
    default_model = Movie

    def get_list(self, status: MovieStatus | None) -> Sequence[Movie]:
        """Unwatched first, newest added first; then latest watched first"""
        statement = select(Movie)
        if status is not None:
            statement = statement.where(Movie.status == status)
        statement = statement.order_by(
            col(Movie.status),
            col(Movie.watched_at).desc().nulls_last(),
            col(Movie.created_at).desc(),
            col(Movie.id).desc(),
        )
        return self.session.exec(statement).all()


class MovieRatingRepository(ModelRepository[MovieRating]):
    """Repository layer for movie ratings"""
    default_model = MovieRating

    def get_for_movies(
        self, movie_ids: Collection[int]
    ) -> Sequence[MovieRating]:
        """Ratings of several movies in one query, oldest first"""
        statement = (
            select(MovieRating)
            .where(col(MovieRating.movie_id).in_(movie_ids))
            .order_by(col(MovieRating.created_at), col(MovieRating.id))
        )
        return self.session.exec(statement).all()

    def get_by_movie_and_user(
        self, movie_id: int, user_id: int
    ) -> MovieRating | None:
        statement = select(MovieRating).where(
            MovieRating.movie_id == movie_id,
            MovieRating.user_id == user_id,
        )
        return self.session.exec(statement).first()
