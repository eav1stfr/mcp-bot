from enum import StrEnum

LINK_MAX_LENGTH = 2048


class PlaceStatus(StrEnum):
    WANT_TO_VISIT = "want_to_visit"
    VISITED = "visited"


class PlaceErrorMessage(StrEnum):
    PLACE_NOT_FOUND = "Place not found"
