from enum import StrEnum


class Person(StrEnum):
    """One of the two users, seen from the user making the request"""
    ME = "me"
    PARTNER = "partner"


class UserErrorMessage(StrEnum):
    UNKNOWN_USER = "No user with this Telegram ID"
    NO_PARTNER = "User has no partner linked"
