from enum import StrEnum

MIN_SCORE = 1
MAX_SCORE = 10

MIN_YEAR = 1888
MAX_YEAR = 2100


class MovieStatus(StrEnum):
    TO_WATCH = "to_watch"
    WATCHED = "watched"


class MovieErrorMessage(StrEnum):
    MOVIE_NOT_FOUND = "Movie not found"
