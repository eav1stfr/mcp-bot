from collections import defaultdict
from collections.abc import Sequence

from app.common.dependencies import DBSessionDep
from app.common.exceptions import NotFound
from app.common.utils import get_now_utc
from app.movies.constants import MovieErrorMessage, MovieStatus
from app.movies.models import Movie, MovieRating
from app.movies.repository import MovieRatingRepository, MovieRepository
from app.movies.schemas import (
    MovieCreateRequest,
    MovieRatingRequest,
    MovieRatingRetrieve,
    MovieRetrieve,
    MovieUpdateRequest,
    MultipleMoviesRetrieve,
)
from app.users.models import User
from app.users.repository import UserRepository


class Service:
    """Service layer for the shared movie list and each user's ratings"""

    def __init__(self, session: DBSessionDep):
        self.movie_repo = MovieRepository(session)
        self.rating_repo = MovieRatingRepository(session)
        self.user_repo = UserRepository(session)

    def list_movies(self, status: MovieStatus | None) -> MultipleMoviesRetrieve:
        """Movies with both users' ratings; no status means all of them"""
        movies = self.movie_repo.get_list(status)
        return MultipleMoviesRetrieve(
            movies=self._retrieve_many(movies), count=len(movies)
        )

    def add_movie(self, actor: User, data: MovieCreateRequest) -> MovieRetrieve:
        movie = Movie(added_by=actor.id, **data.model_dump())
        return self._retrieve(self.movie_repo.create(movie))

    def update_movie(
        self, movie_id: int, data: MovieUpdateRequest
    ) -> MovieRetrieve:
        movie = self._get_movie(movie_id)
        changes = data.model_dump(exclude_unset=True)
        status = changes.pop("status", None)
        movie.sqlmodel_update(changes)
        if status is not None:
            self._set_status(movie, status)
        return self._retrieve(self.movie_repo.update(movie))

    def delete_movie(self, movie_id: int) -> None:
        """Delete a movie along with its ratings"""
        movie = self._get_movie(movie_id)
        self.movie_repo.delete(movie.id)

    def rate_movie(
        self, actor: User, movie_id: int, data: MovieRatingRequest
    ) -> MovieRetrieve:
        """Set the actor's own rating; a rated movie counts as watched"""
        movie = self._get_movie(movie_id)
        rating = self.rating_repo.get_by_movie_and_user(movie.id, actor.id)
        if rating is None:
            rating = MovieRating(movie_id=movie.id, user_id=actor.id)
        rating.sqlmodel_update(data.model_dump())
        self.rating_repo.update_without_commit(rating)

        self._set_status(movie, MovieStatus.WATCHED)
        self.movie_repo.update_without_commit(movie)
        self.movie_repo.commit()
        return self._retrieve(movie)

    def _get_movie(self, movie_id: int) -> Movie:
        movie = self.movie_repo.get(movie_id)
        if movie is None:
            raise NotFound(MovieErrorMessage.MOVIE_NOT_FOUND)
        return movie

    @staticmethod
    def _set_status(movie: Movie, status: MovieStatus) -> None:
        """Change the status and keep watched_at in step with it"""
        if status == MovieStatus.TO_WATCH:
            movie.watched_at = None
        elif movie.watched_at is None:
            movie.watched_at = get_now_utc()
        movie.status = status

    def _retrieve(self, movie: Movie) -> MovieRetrieve:
        return self._retrieve_many([movie])[0]

    def _retrieve_many(self, movies: Sequence[Movie]) -> list[MovieRetrieve]:
        """Attach ratings and raters' names with two queries in total"""
        ratings = self.rating_repo.get_for_movies([m.id for m in movies])
        raters = self.user_repo.get_many({r.user_id for r in ratings})

        ratings_by_movie: dict[int, list[MovieRatingRetrieve]] = defaultdict(
            list
        )
        for rating in ratings:
            ratings_by_movie[rating.movie_id].append(
                MovieRatingRetrieve(
                    user_id=rating.user_id,
                    user_name=raters[rating.user_id].name,
                    score=rating.score,
                    comment=rating.comment,
                    updated_at=rating.updated_at,
                )
            )
        return [
            MovieRetrieve(
                **movie.model_dump(), ratings=ratings_by_movie[movie.id]
            )
            for movie in movies
        ]
