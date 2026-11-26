from fastapi import APIRouter, status

from app.movies.constants import MovieStatus
from app.movies.dependencies import SvcDep
from app.movies.schemas import (
    MovieCreateRequest,
    MovieRatingRequest,
    MovieRetrieve,
    MovieUpdateRequest,
    MultipleMoviesRetrieve,
)
from app.users.dependencies import ActorDep, IsKnownUser

movies_router = APIRouter(prefix="/movies", tags=["movies"])


@movies_router.get(
    "",
    dependencies=[IsKnownUser],
    summary="The shared movie list with both ratings",
    description="Without `status`, returns every movie.",
)
def list_movies(
    svc: SvcDep, status: MovieStatus | None = None
) -> MultipleMoviesRetrieve:
    return svc.list_movies(status)


@movies_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a movie to watch",
)
def add_movie(
    svc: SvcDep, actor: ActorDep, request: MovieCreateRequest
) -> MovieRetrieve:
    return svc.add_movie(actor, request)


@movies_router.patch(
    "/{movie_id}", dependencies=[IsKnownUser], summary="Edit a movie"
)
def update_movie(
    svc: SvcDep, movie_id: int, request: MovieUpdateRequest
) -> MovieRetrieve:
    return svc.update_movie(movie_id, request)


@movies_router.delete(
    "/{movie_id}",
    dependencies=[IsKnownUser],
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a movie and its ratings",
)
def delete_movie(svc: SvcDep, movie_id: int) -> None:
    svc.delete_movie(movie_id)


@movies_router.put(
    "/{movie_id}/rating",
    summary="Set my rating; marks the movie as watched",
)
def rate_movie(
    svc: SvcDep, actor: ActorDep, movie_id: int, request: MovieRatingRequest
) -> MovieRetrieve:
    return svc.rate_movie(actor, movie_id, request)
